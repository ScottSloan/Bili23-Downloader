//=====================================================================
//
// PyStand.cpp -
//
// Created by skywind on 2022/02/03
// Last Modified: 2024/06/19 11:16
//
//=====================================================================
#ifdef _MSC_VER
#define _CRT_SECURE_NO_WARNINGS 1
#endif

#include <shlwapi.h>
#include <string>
#include <string.h>
#include <winbase.h>
#include <wincon.h>

#include <bcrypt.h>
#include <map>

#include "PyStand.h"

#ifdef _MSC_VER
#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "bcrypt.lib")
#endif


//---------------------------------------------------------------------
// dtor
//---------------------------------------------------------------------
PyStand::~PyStand()
{
	if (_hDLL != NULL) {
		FreeLibrary(_hDLL);
		_hDLL = NULL;
	}
}


//---------------------------------------------------------------------
// ctor
//---------------------------------------------------------------------
PyStand::PyStand(const wchar_t *runtime)
{
	_hDLL = NULL;
	_Py_Main = NULL;
	_blob = NULL;
	_blob_size = 0;
	if (CheckEnviron(runtime) == false) {
		exit(1);
	}
	// 必须早于 LoadPython：python3.dll 本身就是被核对的对象之一
	if (VerifyIntegrity() == false) {
		exit(4);
	}
	if (LoadPython() == false) {
		exit(2);
	}
}


//---------------------------------------------------------------------
// ctor for ansi
//---------------------------------------------------------------------
PyStand::PyStand(const char *runtime)
{
	_hDLL = NULL;
	_Py_Main = NULL;
	_blob = NULL;
	_blob_size = 0;
	std::wstring rtp = Ansi2Unicode(runtime);
	if (CheckEnviron(rtp.c_str()) == false) {
		exit(1);
	}
	// 必须早于 LoadPython：python3.dll 本身就是被核对的对象之一
	if (VerifyIntegrity() == false) {
		exit(4);
	}
	if (LoadPython() == false) {
		exit(2);
	}
}


//---------------------------------------------------------------------
// char to wchar_t
//---------------------------------------------------------------------
std::wstring PyStand::Ansi2Unicode(const char *text)
{
	int len = (int)strlen(text);
	std::wstring wide;
	int require = MultiByteToWideChar(CP_ACP, 0, text, len, NULL, 0);
	if (require > 0) {
		wide.resize(require);
		MultiByteToWideChar(CP_ACP, 0, text, len, &wide[0], require);
	}
	return wide;
}


//---------------------------------------------------------------------
// 路径查询：一律按 API 报出来的长度取，不假定 MAX_PATH
//
// 旧写法统一用 wchar_t[MAX_PATH + 10]，路径一旦超过 260 字符就会被悄悄截断，
// 而且这几个 API 的返回值原本都没有检查。后果不是当场报错，而是 _home 算错，
// 最终弹出"Missing embedded Python3"——一条与真正病因毫不相干的提示。
//---------------------------------------------------------------------
static bool QueryCurrentDirectory(std::wstring &out)
{
	DWORD need = GetCurrentDirectoryW(0, NULL);
	if (need == 0) {
		return false;
	}
	std::vector<wchar_t> buf(need + 1);
	DWORD n = GetCurrentDirectoryW((DWORD)buf.size(), &buf[0]);
	if (n == 0 || n >= buf.size()) {
		return false;
	}
	out.assign(&buf[0], n);
	return true;
}


static bool QueryModulePath(std::wstring &out)
{
	// GetModuleFileName 不提供"需要多大"的查询方式，只能逐次翻倍重试：
	// 缓冲不够时它返回的正是缓冲区大小本身，据此判断被截断
	std::vector<wchar_t> buf(MAX_PATH + 1);
	for (;;) {
		DWORD n = GetModuleFileNameW(NULL, &buf[0], (DWORD)buf.size());
		if (n == 0) {
			return false;
		}
		if (n < buf.size() - 1) {
			out.assign(&buf[0], n);
			return true;
		}
		if (buf.size() >= 65536) {
			return false;
		}
		buf.resize(buf.size() * 2);
	}
}


static bool QueryFullPath(const std::wstring &in, std::wstring &out)
{
	DWORD need = GetFullPathNameW(in.c_str(), 0, NULL, NULL);
	if (need == 0) {
		return false;
	}
	std::vector<wchar_t> buf(need + 1);
	DWORD n = GetFullPathNameW(in.c_str(), (DWORD)buf.size(), &buf[0], NULL);
	if (n == 0 || n >= buf.size()) {
		return false;
	}
	out.assign(&buf[0], n);
	return true;
}


//---------------------------------------------------------------------
// init: _args, _argv, _cwd, _pystand, _home, _runtime,
//---------------------------------------------------------------------
bool PyStand::CheckEnviron(const wchar_t *rtp)
{
	// init: _args, _argv
	LPWSTR *argvw;
	int argc;
	_args = GetCommandLineW();
	argvw = CommandLineToArgvW(_args.c_str(), &argc);
	if (argvw == NULL) {
		MessageBoxA(NULL, "Error in CommandLineToArgvW()", "ERROR", MB_OK);
		return false;
	}
	_argv.resize(argc);
	for (int i = 0; i < argc; i++) {
		_argv[i] = argvw[i];
	}
	LocalFree(argvw);

	// init: _cwd (current working directory)
	if (QueryCurrentDirectory(_cwd) == false) {
		MessageBoxW(NULL, L"Cannot query current directory",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	// init: _pystand (full path of PyStand.exe)
	if (QueryModulePath(_pystand) == false) {
		MessageBoxW(NULL, L"Cannot query the path of this executable",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	// init: _home（自身所在目录）
	//
	// 原来是靠 SetCurrentDirectory + GetCurrentDirectory 绕一圈来规范化路径，
	// 那会短暂改动进程的全局状态；GetFullPathName 做的是同一件事，且无副作用。
	{
		size_t cut = _pystand.size();
		for (; cut > 0; cut--) {
			if (_pystand[cut - 1] == L'/') break;
			if (_pystand[cut - 1] == L'\\') break;
		}
		std::wstring parent = _pystand.substr(0, cut);
		if (parent.empty() || QueryFullPath(parent, _home) == false) {
			MessageBoxW(NULL, L"Cannot resolve the home directory",
				L"ERROR", MB_OK | MB_ICONERROR);
			return false;
		}
		// 去掉末尾分隔符，与 GetCurrentDirectory 的旧结果保持一致 ——
		// 后面 _home + L"\\" + rtp 的拼接依赖这一点。"D:\" 这类根目录例外
		while (_home.size() > 3 && (_home.back() == L'\\' || _home.back() == L'/')) {
			_home.pop_back();
		}
	}

	// init: _runtime (embedded python directory)
	bool abspath = false;
	if (wcslen(rtp) >= 3) {
		if (rtp[1] == L':') {
			if (rtp[2] == L'/' || rtp[2] == L'\\')
				abspath = true;
		}
	}
	if (abspath == false) {
		_runtime = _home + L"\\" + rtp;
	}
	else {
		_runtime = rtp;
	}
	std::wstring resolved;
	if (QueryFullPath(_runtime, resolved) == false) {
		std::wstring msg = L"Cannot resolve the runtime path:\r\n" + _runtime;
		MessageBoxW(NULL, msg.c_str(), L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}
	_runtime = resolved;

	// check home
	std::wstring check = _runtime;
	if (!PathFileExistsW(check.c_str())) {
		std::wstring msg = L"Missing embedded Python3 in:\n" + check;
		MessageBoxW(NULL, msg.c_str(), L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	// check python3.dll
	std::wstring check2 = _runtime + L"\\python3.dll";
	if (!PathFileExistsW(check2.c_str())) {
		std::wstring msg = L"Missing python3.dll in:\r\n" + check;
		MessageBoxW(NULL, msg.c_str(), L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	// setup environment
	SetEnvironmentVariableW(L"PYSTAND", _pystand.c_str());
	SetEnvironmentVariableW(L"PYSTAND_HOME", _home.c_str());
	SetEnvironmentVariableW(L"PYSTAND_RUNTIME", _runtime.c_str());

	// unnecessary to init PYSTAND_SCRIPT here.
#if 0
	SetEnvironmentVariableW(L"PYSTAND_SCRIPT", _script.c_str());
#endif

#if 0
	wprintf(L"%s - %s\n", _pystand.c_str(), path);
	MessageBoxW(NULL, _pystand.c_str(), _home.c_str(), MB_OK);
#endif

	return true;
}


//---------------------------------------------------------------------
// 完整性校验
//
// 内嵌源码解决的只是"入口脚本可以被换掉"。剩下的攻击面全在磁盘上：
// site-packages 里随便哪个 .py、runtime\python3.dll、一个新丢进去的 .pth，
// 改任意一处都能在这个带着我们签名的进程里执行任意代码。
//
// 清单列出每个随包文件的 SHA-256，它自己嵌在资源段里，跟着 exe 一起被
// Authenticode 覆盖 —— 所以不需要私钥、不需要非对称签名：想改清单就得改 exe，
// 签名当场失效。
//
// 实测 669 个文件 / 91.8 MB 单线程约 140 ms，相比 PySide6 自身一两秒的导入
// 开销可以忽略，因此不做并行、不做后台异步，一律在加载 Python 之前同步验完。
//---------------------------------------------------------------------

// 这些类型出现在受管目录里却不在清单中，一律拒绝启动。
// 只校验"清单里有的"是不够的 —— 那样往 site-packages 丢一个新的 .pth
// 或 DLL 依然畅通无阻，而这恰恰是最省事的注入手法。
static const wchar_t *kCodeExtensions[] = {
	L"py", L"pyc", L"pyd", L"pyw", L"pyo", L"pyz",
	L"dll", L"exe", L"com", L"ocx", L"sys", L"drv", L"scr",
	L"so", L"pth", L"_pth", L"zip", L"cat",
	// WebUI 的前端产物同样是会被执行的代码，只不过执行它的是浏览器
	L"js", L"mjs", L"html", L"htm", L"css",
	NULL
};

// 白名单外检查只覆盖这几个目录。程序目录下其余位置（便携版的配置、用户
// 顺手放的文件）只在清单里有记录时才核对，不在就放过 —— 否则用户往安装
// 目录里丢个文件就打不开程序了。
static const wchar_t *kManagedDirs[] = {
	L"runtime", L"site-packages", L"bundle", L"webui", NULL
};


static bool IsCodeFile(const std::wstring &rel)
{
	size_t dot = rel.find_last_of(L'.');
	if (dot == std::wstring::npos) {
		return false;
	}
	size_t sep = rel.find_last_of(L'\\');
	if (sep != std::wstring::npos && dot < sep) {
		return false;
	}

	std::wstring ext = rel.substr(dot + 1);
	for (size_t i = 0; i < ext.size(); i++) {
		ext[i] = (wchar_t)towlower(ext[i]);
	}
	for (int i = 0; kCodeExtensions[i] != NULL; i++) {
		if (ext == kCodeExtensions[i]) {
			return true;
		}
	}
	return false;
}


static bool IsManaged(const std::wstring &rel)
{
	for (int i = 0; kManagedDirs[i] != NULL; i++) {
		size_t n = wcslen(kManagedDirs[i]);
		if (rel.size() > n && rel[n] == L'\\' &&
			_wcsnicmp(rel.c_str(), kManagedDirs[i], n) == 0) {
			return true;
		}
	}
	return false;
}


//---------------------------------------------------------------------
// SHA-256 一个文件
//
// FILE_SHARE_READ 而不带 WRITE：校验期间别的进程改不了它，把校验与后续
// 加载之间的时间窗口收窄一点。
//---------------------------------------------------------------------
static bool HashFile(BCRYPT_ALG_HANDLE alg, const std::wstring &path,
	std::vector<BYTE> &buf, BYTE out[32])
{
	HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ,
		NULL, OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (file == INVALID_HANDLE_VALUE) {
		return false;
	}

	BCRYPT_HASH_HANDLE hash = NULL;
	bool ok = false;

	if (BCryptCreateHash(alg, &hash, NULL, 0, NULL, 0, 0) == 0) {
		ok = true;
		for (;;) {
			DWORD got = 0;
			if (ReadFile(file, &buf[0], (DWORD)buf.size(), &got, NULL) == FALSE) {
				ok = false;
				break;
			}
			if (got == 0) {
				break;
			}
			if (BCryptHashData(hash, &buf[0], got, 0) != 0) {
				ok = false;
				break;
			}
		}
		if (ok && BCryptFinishHash(hash, out, 32, 0) != 0) {
			ok = false;
		}
		BCryptDestroyHash(hash);
	}

	CloseHandle(file);
	return ok;
}


//---------------------------------------------------------------------
// 递归收集目录下所有文件的相对路径
//---------------------------------------------------------------------
static void ScanTree(const std::wstring &root, const std::wstring &prefix,
	std::vector<std::wstring> &out)
{
	std::wstring pattern = root;
	if (!prefix.empty()) {
		pattern += L"\\" + prefix;
	}
	pattern += L"\\*";

	WIN32_FIND_DATAW fd;
	HANDLE find = FindFirstFileW(pattern.c_str(), &fd);
	if (find == INVALID_HANDLE_VALUE) {
		return;
	}

	do {
		if (wcscmp(fd.cFileName, L".") == 0 || wcscmp(fd.cFileName, L"..") == 0) {
			continue;
		}
		std::wstring rel = prefix.empty() ?
			std::wstring(fd.cFileName) : prefix + L"\\" + fd.cFileName;

		if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
			// 与清单生成侧的 SKIP_DIRS 对齐
			if (wcscmp(fd.cFileName, L"__pycache__") == 0) {
				continue;
			}
			ScanTree(root, rel, out);
		}
		else {
			out.push_back(rel);
		}
	} while (FindNextFileW(find, &fd));

	FindClose(find);
}


//---------------------------------------------------------------------
// 收紧 DLL 搜索路径
//
// 默认的搜索顺序里含有 exe 所在目录与 PATH，在那里放一个与系统 DLL 同名的
// 文件就会被优先加载 —— 而加载它的是一个带着我们代码签名的进程。
// SetDefaultDllDirectories 把范围压到 System32 加上显式登记的目录，
// AddDllDirectory 再把 runtime 放回来：python3.dll 要在那里找到
// python3XX.dll 和自己的依赖。
//
// 这两个 API 需要 Windows 8（Win7 得装 KB2533623），而 Win7 兼容版仍要能跑，
// 所以动态取地址，取不到就退回原先的 SetDllDirectory。
//
// 对静态导入的 shlwapi.dll 无能为力 —— 那是进程启动时就由加载器解析的，
// 任何代码都来不及干预；好在它属于 KnownDLLs，系统保证从 System32 取。
//---------------------------------------------------------------------
#ifndef LOAD_LIBRARY_SEARCH_SYSTEM32
#define LOAD_LIBRARY_SEARCH_SYSTEM32 0x00000800
#endif
#ifndef LOAD_LIBRARY_SEARCH_USER_DIRS
#define LOAD_LIBRARY_SEARCH_USER_DIRS 0x00000400
#endif

typedef BOOL (WINAPI *t_SetDefaultDllDirectories)(DWORD);
typedef PVOID (WINAPI *t_AddDllDirectory)(PCWSTR);

static bool HardenDllSearch(const std::wstring &runtime)
{
	HMODULE k32 = GetModuleHandleW(L"kernel32.dll");
	if (k32 == NULL) {
		return false;
	}

	t_SetDefaultDllDirectories set_dirs =
		(t_SetDefaultDllDirectories)(void*)GetProcAddress(k32, "SetDefaultDllDirectories");
	t_AddDllDirectory add_dir =
		(t_AddDllDirectory)(void*)GetProcAddress(k32, "AddDllDirectory");

	// 两个必须成对可用：只收紧却加不回 runtime，python3.dll 就找不到依赖了
	if (set_dirs == NULL || add_dir == NULL) {
		return false;
	}
	if (set_dirs(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS) == FALSE) {
		return false;
	}
	if (add_dir(runtime.c_str()) == NULL) {
		return false;
	}
	return true;
}


//---------------------------------------------------------------------
// load python
//---------------------------------------------------------------------
bool PyStand::LoadPython()
{
	std::wstring runtime = _runtime;
	std::wstring previous;

	// save current directory
	wchar_t path[MAX_PATH + 10];
	GetCurrentDirectoryW(MAX_PATH + 1, path);
	previous = path;

	// python dll must be load under "runtime"
	SetCurrentDirectoryW(runtime.c_str());
	if (HardenDllSearch(runtime) == false) {
		SetDllDirectoryW(runtime.c_str());
	}

	auto pydll = runtime + L"\\python3.dll";
	// LoadLibrary
	_hDLL = (HINSTANCE)LoadLibraryW(pydll.c_str());
	if (_hDLL) {
		_Py_Main = (t_Py_Main)GetProcAddress(_hDLL, "Py_Main");
	}

	// restore director
	SetCurrentDirectoryW(previous.c_str());

	if (_hDLL == NULL) {
		std::wstring msg = L"Cannot load python3.dll from:\r\n" + runtime;
		MessageBoxW(NULL, msg.c_str(), L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}
	else if (_Py_Main == NULL) {
		std::wstring msg = L"Cannot find Py_Main() in:\r\n";
		msg += pydll;
		MessageBoxW(NULL, msg.c_str(), L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}
	return true;
}


//---------------------------------------------------------------------
// run string
//---------------------------------------------------------------------
int PyStand::RunString(const wchar_t *script)
{
	if (_Py_Main == NULL) {
		return -1;
	}
	int hr = 0;
	int i;
	_py_argv.resize(0);
	// init arguments
	//
	// _argv 正常至少有一项（程序自身路径），但 CommandLineToArgvW 在极端情况下
	// 可能给出空列表，而这里原本是无条件取 _argv[0]
	_py_argv.push_back(_argv.empty() ? _pystand : _argv[0]);
	_py_argv.push_back(L"-I");
	_py_argv.push_back(L"-s");
	_py_argv.push_back(L"-S");
	// 强制 UTF-8 模式。
	//
	// 上面的 -I 蕴含 -E，会屏蔽掉 PYTHONUTF8，所以只能走 -X。不开的话，
	// Python 3.15 之前 sys.stdout 与 open() 都跟随系统 ANSI 代码页（简中即 GBK），
	// 于是中文经管道输出就是乱码 —— MCP 的 stdio 桥接首当其冲。
	//
	// 已确认应用侧不受影响：所有文本 IO 都显式写了 encoding，ffmpeg 的子进程
	// 指定了 encoding="utf-8"，aria2 则直接把输出重定向到文件句柄。
	_py_argv.push_back(L"-X");
	_py_argv.push_back(L"utf8");
	_py_argv.push_back(L"-c");
	_py_argv.push_back(script);
	for (i = 1; i < (int)_argv.size(); i++) {
		_py_argv.push_back(_argv[i]);
	}
	// finalize arguments
	_py_args.resize(0);
	for (i = 0; i < (int)_py_argv.size(); i++) {
		_py_args.push_back((wchar_t*)_py_argv[i].c_str());
	}
	hr = _Py_Main((int)_py_args.size(), &_py_args[0]);
	return hr;
}


//---------------------------------------------------------------------
// run ansi string
//---------------------------------------------------------------------
int PyStand::RunString(const char *script)
{
	std::wstring text = Ansi2Unicode(script);
	return RunString(text.c_str());
}



//---------------------------------------------------------------------
// static init script
//---------------------------------------------------------------------
#ifndef PYSTAND_STATIC_NAME
#define PYSTAND_STATIC_NAME "_pystand_static.int"
#endif


//---------------------------------------------------------------------
// 逐个核对随包文件
//---------------------------------------------------------------------
bool PyStand::VerifyIntegrity()
{
#ifdef PYSTAND_EMBED_APP
	struct Record { BYTE hash[32]; bool seen; };
	std::map<std::wstring, Record> table;

	// ---- 取出清单 ----
	HRSRC res = FindResourceW(NULL, L"INTEGRITY", (LPCWSTR)RT_RCDATA);
	HGLOBAL handle = res ? LoadResource(NULL, res) : NULL;
	const BYTE *data = handle ? (const BYTE*)LockResource(handle) : NULL;
	DWORD size = res ? SizeofResource(NULL, res) : 0;

	// 没有清单就拒绝启动，而不是放行。清单删不掉——那要改 exe，签名会失效——
	// 所以真正会走到这里的只有"构建时漏了清单"，那种产物不该能跑起来。
	if (data == NULL || size < 8 || memcmp(data, "PSM1", 4) != 0) {
		MessageBoxW(NULL,
			L"Integrity manifest is missing or malformed.\r\n"
			L"This build is not usable; please obtain an official release.",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	DWORD count = *(const DWORD*)(data + 4);
	DWORD pos = 8;

	for (DWORD i = 0; i < count; i++) {
		if (pos + 2 > size) break;
		WORD len = *(const WORD*)(data + pos);
		pos += 2;
		if (pos + len + 32 > size) break;

		int wide = MultiByteToWideChar(CP_UTF8, 0, (const char*)(data + pos), len, NULL, 0);
		std::wstring rel;
		if (wide > 0) {
			rel.resize(wide);
			MultiByteToWideChar(CP_UTF8, 0, (const char*)(data + pos), len, &rel[0], wide);
		}
		pos += len;

		Record rec;
		memcpy(rec.hash, data + pos, 32);
		rec.seen = false;
		pos += 32;

		if (!rel.empty()) {
			table[rel] = rec;
		}
	}

	if (table.size() != count) {
		MessageBoxW(NULL, L"Integrity manifest is truncated.",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	// ---- 遍历磁盘并核对 ----
	BCRYPT_ALG_HANDLE alg = NULL;
	if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) != 0) {
		MessageBoxW(NULL, L"Cannot initialise SHA-256 provider.",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	// 启动器自己不在清单里：它由代码签名保护，也没法自己算自己的哈希
	std::wstring self = _pystand.size() > _home.size() + 1 ?
		_pystand.substr(_home.size() + 1) : std::wstring();

	std::vector<std::wstring> files;
	ScanTree(_home, L"", files);

	std::vector<BYTE> buf(1 << 20);
	std::wstring failure;

	for (size_t i = 0; i < files.size() && failure.empty(); i++) {
		const std::wstring &rel = files[i];
		if (!self.empty() && _wcsicmp(rel.c_str(), self.c_str()) == 0) {
			continue;
		}

		std::map<std::wstring, Record>::iterator it = table.find(rel);
		if (it == table.end()) {
			// 清单里没有：受管目录下的可执行类型一律拒绝，其余放过
			if (IsManaged(rel) && IsCodeFile(rel)) {
				failure = L"Unexpected file:\r\n" + rel;
			}
			continue;
		}

		BYTE digest[32];
		if (HashFile(alg, _home + L"\\" + rel, buf, digest) == false) {
			failure = L"Cannot read:\r\n" + rel;
			continue;
		}
		if (memcmp(digest, it->second.hash, 32) != 0) {
			failure = L"Modified file:\r\n" + rel;
			continue;
		}
		it->second.seen = true;
	}

	// 清单里有、磁盘上却没有的，同样是被动过
	if (failure.empty()) {
		for (std::map<std::wstring, Record>::iterator it = table.begin();
			it != table.end(); ++it) {
			if (it->second.seen == false) {
				failure = L"Missing file:\r\n" + it->first;
				break;
			}
		}
	}

	BCryptCloseAlgorithmProvider(alg, 0);

	if (!failure.empty()) {
		std::wstring msg =
			L"Integrity check failed. The installation has been modified "
			L"and will not be started.\r\n\r\n" + failure;
		MessageBoxW(NULL, msg.c_str(), L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}
#endif
	return true;
}


//---------------------------------------------------------------------
// 取出嵌在自身资源段里的 app.zip
//
// 资源是映像的一部分，LockResource 拿到的指针直接指向已映射的页面，
// 既不需要复制也不需要释放；进程活着它就一直有效。
//---------------------------------------------------------------------
bool PyStand::LoadAppBlob()
{
#ifdef PYSTAND_EMBED_APP
	HRSRC res = FindResourceW(NULL, L"APP_ZIP", (LPCWSTR)RT_RCDATA);
	if (res == NULL) {
		MessageBoxW(NULL, L"Missing embedded APP_ZIP resource",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	HGLOBAL handle = LoadResource(NULL, res);
	if (handle == NULL) {
		MessageBoxW(NULL, L"Cannot load APP_ZIP resource",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	_blob = (const BYTE*)LockResource(handle);
	_blob_size = SizeofResource(NULL, res);

	if (_blob == NULL || _blob_size == 0) {
		MessageBoxW(NULL, L"Embedded APP_ZIP resource is empty",
			L"ERROR", MB_OK | MB_ICONERROR);
		return false;
	}

	// 地址与长度交给 Python 侧，由 ctypes.string_at() 取回内容。同一个
	// 进程的地址空间，不存在跨进程传递指针的问题；-I 模式下解释器也不会
	// 理会外部传进来的环境变量
	//
	// 这里不能用 wsprintfW：那是 user32 的精简实现，不认 "ll" 长度修饰符，
	// %llu 会被拆成 %l 加上字面量 "lu"，指针地址就此变成一串废话。
	// to_wstring 没有格式串，也就没有这类陷阱。
	std::wstring desc = std::to_wstring((unsigned long long)(uintptr_t)_blob)
		+ L":" + std::to_wstring((unsigned long long)_blob_size);
	SetEnvironmentVariableW(L"PYSTAND_APP_BLOB", desc.c_str());
#endif
	return true;
}


//---------------------------------------------------------------------
// LoadScript()
//---------------------------------------------------------------------
int PyStand::DetectScript()
{
#ifdef PYSTAND_EMBED_APP
	// 内嵌模式下不存在"外部入口脚本"这个概念。这里必须直接返回，
	// 绝不能保留磁盘探测作为兜底：只要还认 PyStand.int / PyStand.py，
	// 在目录里放一个同名文件就能绕开内嵌源码，签名的启动器又变回了
	// 谁都能拿去跑任意代码的通用 loader。
	//
	// PYSTAND_SCRIPT 仍然导出，指向内嵌入口在概念上对应的位置 ——
	// 该路径并不存在于磁盘，仅供需要它的代码拼接路径之用。
	_script = _home + L"\\script\\main.py";
	SetEnvironmentVariableW(L"PYSTAND_SCRIPT", _script.c_str());
	return LoadAppBlob() ? 0 : -1;
#else
	// init: _script (init script like PyStand.int or PyStand.py)
	int size = (int)_pystand.size() - 1;
	for (; size >= 0; size--) {
		if (_pystand[size] == L'.') break;
	}
	if (size < 0) size = (int)_pystand.size();
	std::wstring main = _pystand.substr(0, size);
	std::vector<const wchar_t*> exts;
	std::vector<std::wstring> scripts;
	_script.clear();
	// 注意用 ifndef：写成 #if !(PYSTAND_DISABLE_STATIC) 时，宏没定义就靠
	// 预处理器把未知标识符当 0 来求值，能用但语义脆弱，开了警告还会报 C4668
#ifndef PYSTAND_DISABLE_STATIC
	std::wstring test;
	test = _home + L"\\" + Ansi2Unicode(PYSTAND_STATIC_NAME);
	if (PathFileExistsW(test.c_str())) {
		_script = test;
	}
#endif
	if (_script.empty()) {
		exts.push_back(L".int");
		exts.push_back(L".py");
		exts.push_back(L".pyw");
		for (int i = 0; i < (int)exts.size(); i++) {
			std::wstring test = main + exts[i];
			scripts.push_back(test);
			if (PathFileExistsW(test.c_str())) {
				_script = test;
				break;
			}
		}
		if (_script.size() == 0) {
			std::wstring msg = L"Can't find either of:\r\n";
			for (int j = 0; j < (int)scripts.size(); j++) {
				msg += scripts[j] + L"\r\n";
			}
			MessageBoxW(NULL, msg.c_str(), L"ERROR", MB_OK | MB_ICONERROR);
			return -1;
		}
	}
	SetEnvironmentVariableW(L"PYSTAND_SCRIPT", _script.c_str());
	return 0;
#endif
}


//---------------------------------------------------------------------
// init script
//---------------------------------------------------------------------
//---------------------------------------------------------------------
// 引导脚本
//
// 通过 Py_Main 的 -c 传入，是解释器起来后执行的第一段 Python。
//
// 内容必须全部是 ASCII：RunString(const char*) 会用 Ansi2Unicode 按系统
// ANSI 代码页做转换，源文件里的中文到了那边就是乱码。因此说明一律写在
// 字符串外面的 C++ 注释里，脚本内部只用英文。
//---------------------------------------------------------------------
const char *init_script =
R"PY(
import sys
import os
import site
PYSTAND = os.environ['PYSTAND']
PYSTAND_HOME = os.environ['PYSTAND_HOME']
PYSTAND_RUNTIME = os.environ['PYSTAND_RUNTIME']
PYSTAND_SCRIPT = os.environ['PYSTAND_SCRIPT']
sys.path_origin = [n for n in sys.path]
sys.PYSTAND = PYSTAND
sys.PYSTAND_HOME = PYSTAND_HOME
sys.PYSTAND_SCRIPT = PYSTAND_SCRIPT
def MessageBox(msg, info = 'Message'):
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, str(msg), str(info), 0 | 0x10)
    return 0
os.MessageBox = MessageBox
)PY"
#ifndef PYSTAND_CONSOLE
// 标准流的接管必须是"兜底"而不是"无条件"。
//
// GUI 子系统的进程默认不带控制台，Python 的 sys.stdout / sys.stderr 会是 None，
// 此时任何一句 print() 都会抛异常，所以要给它们找个去处（控制台或 devnull）。
//
// 但进程由父进程用管道拉起时（例如被 AI 客户端当作 stdio 服务器启动），
// sys.stdout 本身是有效的、指向那根管道。这种情况下再去接管，就等于把程序
// 唯一的输出通道换成了 devnull —— 对面只会看到进程活着却一个字节都收不到。
R"PY(
if sys.stdout is None or sys.stderr is None:
    try:
        fd = os.open('CONOUT$', os.O_RDWR | os.O_BINARY)
        fp = os.fdopen(fd, 'w')
        if sys.stdout is None: sys.stdout = fp
        if sys.stderr is None: sys.stderr = fp
        attached = True
    except Exception as e:
        attached = False
        try:
            fp = open(os.devnull, 'w', errors='ignore')
            if sys.stdout is None: sys.stdout = fp
            if sys.stderr is None: sys.stderr = fp
        except:
            pass
else:
    attached = True
)PY"
#endif
#ifdef PYSTAND_EMBED_APP
// 搜索路径：只登记目录，不再调用 site.addsitedir()。
//
// addsitedir 会顺带执行目录下每个 .pth 文件里以 import 开头的行 —— 那是一条
// 无人看守的执行入口，往 site-packages 里丢一个 .pth 就能在本进程里跑任意代码，
// 而这个进程带着我们的代码签名。
//
// 代价是 pywin32 的那份 .pth 也不再自动生效，它是真实依赖（qframelesswindow
// 的无边框窗口要 win32api/win32con/win32gui），所以下面把它的内容固化过来。
// 顺序不能动：pywin32_bootstrap 自己就在 win32\lib 下，得先让那个目录进 path。
R"PY(
for n in ['.', 'lib', 'site-packages', 'runtime']:
    test = os.path.abspath(os.path.join(PYSTAND_HOME, n))
    if os.path.isdir(test) and test not in sys.path:
        sys.path.append(test)
_sp = os.path.abspath(os.path.join(PYSTAND_HOME, 'site-packages'))
for _sub in [('win32',), ('win32', 'lib'), ('Pythonwin',)]:
    _p = os.path.join(_sp, *_sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.append(_p)
try:
    import pywin32_bootstrap
except ImportError:
    pass
)PY"
// 应用模块直接从资源段里的 zip 取用，磁盘上不存在对应文件。
//
// zip 与 exe 一同被 Authenticode 覆盖，改一个字节签名就失效 —— 签名的启动器
// 因此不可能被拿去跑别的代码。
//
// 每个模块在 zip 里存了 .py 和 .pyc 两份：.pyc 用于执行，省掉每次启动重新编译；
// .py 供 get_source() 使用，崩溃日志里才会有源码行而不是光秃秃的行号。
// __file__ 指向 <PYSTAND_HOME>\script\<相对路径> —— 这个位置并不存在，但形态与
// 内嵌之前完全一致，依赖它反推路径的代码（如 web/static.py 定位 webui/dist）
// 因此不需要任何改动。
//
// _dirs 收的是 PEP 420 命名空间包：项目里多数目录并没有 __init__.py（gui、
// util/common、util/auth 等等都是），磁盘上由 FileFinder 兜着，换成自己的
// finder 就得把这些中间目录也认出来，否则 import util.common 会直接失败。
// 它们不带 __file__ —— 真实的命名空间包也没有，行为保持一致。
R"PY(
import ctypes
import io
import marshal
import zipfile
import importlib.util
import importlib.machinery

_desc = os.environ['PYSTAND_APP_BLOB'].split(':')
_zf = zipfile.ZipFile(io.BytesIO(ctypes.string_at(int(_desc[0]), int(_desc[1]))))
_root = os.path.join(PYSTAND_HOME, 'script')

class _AppLoader:
    def __init__(self, arc, is_pkg):
        self._arc = arc
        self._is_pkg = is_pkg

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(self.get_code(module.__name__), module.__dict__)

    def get_code(self, fullname):
        try:
            data = _zf.read(self._arc[:-3] + '.pyc')
        except KeyError:
            data = b''
        if data[:4] == importlib.util.MAGIC_NUMBER:
            return marshal.loads(data[16:])
        return compile(self.get_source(fullname), self.display_name(),
                       'exec', dont_inherit = True)

    def get_source(self, fullname):
        return _zf.read(self._arc).decode('utf-8')

    def is_package(self, fullname):
        return self._is_pkg

    def get_filename(self, fullname):
        return os.path.join(_root, self._arc.replace('/', os.sep))

    def display_name(self):
        return 'script/' + self._arc

class _AppFinder:
    def __init__(self):
        self._mods = {}
        self._dirs = set()
        for name in _zf.namelist():
            if not name.endswith('.py'):
                continue
            parts = name[:-3].split('/')
            if parts[-1] == '__init__':
                key, pkg = '.'.join(parts[:-1]), True
            else:
                key, pkg = '.'.join(parts), False
            if key:
                self._mods[key] = (name, pkg)
            for i in range(1, len(parts)):
                self._dirs.add('.'.join(parts[:i]))

    def find_spec(self, fullname, path = None, target = None):
        hit = self._mods.get(fullname)
        if hit is not None:
            loader = _AppLoader(hit[0], hit[1])
            origin = loader.get_filename(fullname)
            spec = importlib.machinery.ModuleSpec(fullname, loader,
                                                  origin = origin, is_package = hit[1])
            spec.has_location = True
            if hit[1]:
                spec.submodule_search_locations = [os.path.dirname(origin)]
            return spec
        if fullname in self._dirs:
            spec = importlib.machinery.ModuleSpec(fullname, None, is_package = True)
            spec.submodule_search_locations = [
                os.path.join(_root, fullname.replace('.', os.sep))]
            return spec
        return None

sys.meta_path.insert(0, _AppFinder())

os.chdir(PYSTAND_HOME)
if not hasattr(sys, 'frozen'):
    sys.frozen = True
sys.argv = [PYSTAND_SCRIPT] + sys.argv[1:]

def _pystand_run():
    from main import _main
    _main()
)PY"
#else
R"PY(
for n in ['.', 'lib', 'site-packages', 'runtime']:
    test = os.path.abspath(os.path.join(PYSTAND_HOME, n))
    if os.path.exists(test):
        site.addsitedir(test)
sys.argv = [PYSTAND_SCRIPT] + sys.argv[1:]

def _pystand_run():
    text = open(PYSTAND_SCRIPT, 'rb').read()
    environ = {'__file__': PYSTAND_SCRIPT, '__name__': '__main__'}
    environ['__package__'] = None
    exec(compile(text, PYSTAND_SCRIPT, 'exec'), environ)
)PY"
#endif
#ifndef PYSTAND_CONSOLE
R"PY(
try:
    _pystand_run()
except Exception:
    if attached:
        raise
    import traceback, io
    sio = io.StringIO()
    traceback.print_exc(file = sio)
    os.MessageBox(sio.getvalue(), 'Error')
)PY"
#else
R"PY(
_pystand_run()
)PY"
#endif
"";


//---------------------------------------------------------------------
// main
//---------------------------------------------------------------------

//! flag: -static
//! src:
//! link: stdc++, shlwapi, resource.o
//! prebuild: windres resource.rc -o resource.o
//! mode: win
//! int: objs

#ifdef PYSTAND_CONSOLE
int main()
#else
int WINAPI
WinMain(HINSTANCE hInst, HINSTANCE hPrevInst, LPSTR args, int show)
#endif
{
	PyStand ps("runtime");
	if (ps.DetectScript() != 0) {
		return 3;
	}
#ifndef PYSTAND_CONSOLE
	// 附加到父进程的控制台，让从终端启动时能看到输出。
	//
	// 但 freopen 之前必须先确认这个流没有被父进程重定向过：进程若是被管道
	// 拉起的（例如当作 stdio 服务器供 AI 客户端调用），fd 1 本来指向那根管道，
	// 无条件 freopen 会把它改指到控制台 —— 写入照样"成功"，数据却再也到不了
	// 管道对面，表现为对方一个字节都收不到。
	//
	// 重定向过的流，GetFileType 会返回 FILE_TYPE_PIPE 或 FILE_TYPE_DISK；
	// 未重定向时是 FILE_TYPE_CHAR（控制台）或 FILE_TYPE_UNKNOWN（无句柄）。
	if (AttachConsole(ATTACH_PARENT_PROCESS)) {
		DWORD out_type = GetFileType(GetStdHandle(STD_OUTPUT_HANDLE));
		DWORD err_type = GetFileType(GetStdHandle(STD_ERROR_HANDLE));

		if (out_type != FILE_TYPE_PIPE && out_type != FILE_TYPE_DISK) {
			freopen("CONOUT$", "w", stdout);
		}
		if (err_type != FILE_TYPE_PIPE && err_type != FILE_TYPE_DISK) {
			freopen("CONOUT$", "w", stderr);
		}
		int fd = _fileno(stdout);
		if (fd >= 0) {
			std::string fn = std::to_string(fd);
			SetEnvironmentVariableA("PYSTAND_STDOUT", fn.c_str());
		}
		fd = _fileno(stdin);
		if (fd >= 0) {
			std::string fn = std::to_string(fd);
			SetEnvironmentVariableA("PYSTAND_STDIN", fn.c_str());
		}
	}
#endif
	int hr = ps.RunString(init_script);
	// printf("finalize\n");
	return hr;
}


