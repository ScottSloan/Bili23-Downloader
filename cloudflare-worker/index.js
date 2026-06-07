/**
 * bili23-AISum — Cloudflare Worker
 *
 * 部署为 Cloudflare Workers AI 中转服务，供 bili23-AISum 客户端调用。
 *
 * ================================================================
 * 部署步骤
 * ================================================================
 *
 * 1. 在 Cloudflare Dashboard 创建新 Worker：
 *    https://dash.cloudflare.com/ → Workers & Pages → Create Application → Create Worker
 *
 * 2. 将本文件内容粘贴到 Worker 编辑器中，点击 "Save and Deploy"
 *
 * 3. 绑定 Workers AI（必需）：
 *    Worker 设置 → Settings → AI → 点击 "Add AI binding"
 *    Binding Name: AI
 *    （绑定整个 Workers AI 目录，不指定具体模型。代码中通过下方 DEFAULT_MODEL 常量选择模型）
 *
 * 4. （可选）调整默认模型：
 *    修改下方 DEFAULT_MODEL 常量，或客户端请求中传入 model 字段
 *    常用模型:
 *      @cf/meta/llama-3.2-3b-instruct  — 轻量文本模型
 *      @cf/meta/llama-3.1-8b-instruct  — 更大模型（需装订付费）
 *      @cf/deepseek-ai/deepseek-r1-distill-qwen-32b — 推理模型
 *
 * 5. （可选）添加 API Token 认证：
 *    Worker 设置 → Variables and Secrets → Add Secret:
 *       名称: API_TOKEN    值: 你的自定义 token
 *   客户端在设置中填写相同的 token 即可
 *
 * 6. 获取 Worker URL：
 *    Worker 详情页 → Preview URL 或绑定自定义域名
 *   例如: https://your-worker-name.your-subdomain.workers.dev
 *
 * 7. 在 bili23-AISum 客户端 → Settings → Cloudflare AI 中填入：
 *   - API Endpoint: https://your-worker-name.your-subdomain.workers.dev
 *   - API Token: （如果设置了 Secret 则填写，否则留空）
 *
 * ================================================================
 * 使用方式
 * ================================================================
 *
 * 客户端发送请求：
 *
 *   POST /               JSON body { model, messages } → AI 文本对话
 *   POST /transcribe     multipart/form-data { file } → whisper 转录（仅返回文本）
 *   POST （Content-Type: multipart）→ 文件上传 + AI 总结
 *
 * AI 模型支持的输入类型：
 *   - 文本对话: 任意 Workers AI 支持的 LLM 模型
 *   - 文件上传: 需模型支持多模态输入（音频/视频/图片）
 */

// -------------------------------- AI 路由 --------------------------------
export default {
  async fetch(request, env) {

    // CORS 预检
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
      });
    }

    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    const url = new URL(request.url);

    // ---- /transcribe 专用端点：whisper 转录 ----
    if (url.pathname === "/transcribe") {
      return handleTranscribe(request, env);
    }

    try {
      let model;
      let aiInput;
      const contentType = request.headers.get("content-type") || "";

      if (contentType.includes("multipart/form-data")) {
        // 文件上传模式
        const formData = await request.formData();
        model = formData.get("model") || "@cf/meta/llama-3.2-3b-instruct";
        const prompt = formData.get("prompt") || "请总结以下内容";
        const file = formData.get("file");

        if (!file) {
          return new Response(JSON.stringify({ error: "No file uploaded" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }

        // 读取文件内容
        const fileBytes = await file.arrayBuffer();
        const fileType = file.type;

        if (fileType.startsWith("image/") || fileType.startsWith("video/")) {
          // 图片/视频：作为多模态输入
          const base64 = btoa(
            String.fromCharCode(...new Uint8Array(fileBytes))
          );
          aiInput = {
            messages: [
              {
                role: "user",
                content: [
                  { type: "text", text: prompt },
                  {
                    type: "image_url",
                    image_url: { url: `data:${fileType};base64,${base64}` },
                  },
                ],
              },
            ],
          };
        } else if (fileType.startsWith("audio/")) {
          // 音频：直接传二进制
          const base64 = btoa(
            String.fromCharCode(...new Uint8Array(fileBytes))
          );
          aiInput = {
            audio: base64,
          };
          // 音频模型需要特殊处理，使用专用端点
          if (model === "@cf/meta/llama-3.2-3b-instruct") {
            // 该模型不支持音频，改用 whisper 转文字
            model = "@cf/openai/whisper";
            aiInput = { audio: [...new Uint8Array(fileBytes)] };
          }
        } else {
          // 文本文件：直接读取
          const text = new TextDecoder().decode(fileBytes);
          aiInput = {
            messages: [
              { role: "user", content: `${prompt}\n\n${text}` },
            ],
          };
        }
      } else {
        // JSON 模式（纯文本对话）
        const body = await request.json();
        model = body.model || "@cf/meta/llama-3.2-3b-instruct";
        const messages = body.messages || [];
        aiInput = { messages };
      }

      // 调用 Workers AI
      const aiResponse = await env.AI.run(model, aiInput);

      return new Response(JSON.stringify({ result: aiResponse }), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: err.message }),
        {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        }
      );
    }
  },
};

// -------------------------------- Whisper 转录 --------------------------------
async function handleTranscribe(request, env) {
  let file;
  try {
    const formData = await request.formData();
    file = formData.get("file");
  } catch (err) {
    return new Response(JSON.stringify({ error: "Invalid form data" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!file) {
    return new Response(JSON.stringify({ error: "No file uploaded" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const fileBytes = await file.arrayBuffer();
    const aiResponse = await env.AI.run("@cf/openai/whisper", {
      audio: [...new Uint8Array(fileBytes)],
    });

    // whisper 返回 { text: "..." }
    const text = aiResponse.text || JSON.stringify(aiResponse);

    return new Response(JSON.stringify({ result: { response: text } }), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: err.message }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      }
    );
  }
}
