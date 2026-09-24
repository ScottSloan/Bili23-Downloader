cmake_minimum_required(VERSION 3.10)

project (PyStand LANGUAGES CXX RC)

option(PYSTAND_CONSOLE "Build PyStand as a console application." OFF)

# 把应用源码嵌进可执行文件。开启后 loader 不再从磁盘读取任何入口脚本 ——
# 源码随 exe 一同被代码签名覆盖，签名过的启动器也就无法被拿去跑别的代码。
option(PYSTAND_EMBED_APP "Embed application source zip into the executable." OFF)
set(PYSTAND_APP_ZIP "" CACHE FILEPATH "app.zip built by scripts/build_app_zip.py")
set(PYSTAND_MANIFEST_BIN "" CACHE FILEPATH "manifest.bin built by scripts/gen_manifest.py")

# 版本号。唯一来源在应用侧（util/common/config.py 里 APPConfig 的 app_version），
# 由 scripts/build_release.ps1 读出来传进来，这里只负责补齐成四段并生成
# resource.rc 与 manifest 共用的那份定义 —— 两处各写各的时候错过好几次。
if (NOT PYSTAND_APP_VERSION)
	set(PYSTAND_APP_VERSION "0.0.0")
endif()

string(REPLACE "." ";" _ver_parts "${PYSTAND_APP_VERSION}")
while(1)
	list(LENGTH _ver_parts _ver_len)
	if (_ver_len GREATER_EQUAL 4)
		break()
	endif()
	list(APPEND _ver_parts "0")
endwhile()
list(SUBLIST _ver_parts 0 4 _ver_parts)
list(JOIN _ver_parts "," APP_VER_CSV)
list(JOIN _ver_parts "." APP_VER_STR)

message(STATUS "PyStand 版本: ${APP_VER_STR}")

file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/version.h"
	"// 由 CMakeLists.txt 生成，勿手工编辑
"
	"#define APP_VER_CSV ${APP_VER_CSV}
"
	"#define APP_VER_STR \"${APP_VER_STR}\"
")

configure_file(main.manifest.in "${CMAKE_CURRENT_BINARY_DIR}/main.manifest" @ONLY)

# sources
set(sources
	PyStand.cpp
	resource.rc
	)

if (PYSTAND_CONSOLE)
	add_executable(PyStand ${sources})
	target_compile_definitions(PyStand PRIVATE PYSTAND_CONSOLE)
else()
	add_executable(PyStand WIN32 ${sources})
endif()

if (PYSTAND_EMBED_APP)
	if (NOT PYSTAND_APP_ZIP)
		message(FATAL_ERROR "PYSTAND_EMBED_APP 已开启，但没有指定 PYSTAND_APP_ZIP")
	endif()
	if (NOT EXISTS "${PYSTAND_APP_ZIP}")
		message(FATAL_ERROR "找不到 app.zip：${PYSTAND_APP_ZIP}")
	endif()
	# 清单不是可选项：缺了它 loader 会拒绝启动（见 VerifyIntegrity），
	# 与其产出一个跑不起来的 exe，不如在这里就让构建失败
	if (NOT PYSTAND_MANIFEST_BIN)
		message(FATAL_ERROR "PYSTAND_EMBED_APP 已开启，但没有指定 PYSTAND_MANIFEST_BIN")
	endif()
	if (NOT EXISTS "${PYSTAND_MANIFEST_BIN}")
		message(FATAL_ERROR "找不到 manifest.bin：${PYSTAND_MANIFEST_BIN}")
	endif()

	# 资源脚本里写的是裸文件名，复制到构建目录供资源编译器就近取用；
	# 换了内容就要重新编资源，因此把两者都列进 OBJECT_DEPENDS
	configure_file("${PYSTAND_APP_ZIP}" "${CMAKE_CURRENT_BINARY_DIR}/app.zip" COPYONLY)
	configure_file("${PYSTAND_MANIFEST_BIN}" "${CMAKE_CURRENT_BINARY_DIR}/manifest.bin" COPYONLY)

	target_compile_definitions(PyStand PRIVATE PYSTAND_EMBED_APP)

	set_property(SOURCE resource.rc APPEND PROPERTY
		OBJECT_DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/app.zip"
		               "${CMAKE_CURRENT_BINARY_DIR}/manifest.bin")

endif()

# version.h、main.manifest 以及内嵌用的 app.zip / manifest.bin 都落在构建目录
target_include_directories(PyStand PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if (NOT MSVC)
	# windres 不吃 target_include_directories，得直接给 -I
	set(CMAKE_RC_FLAGS "${CMAKE_RC_FLAGS} -I \"${CMAKE_CURRENT_BINARY_DIR}\"")
endif()

# static link
#
# 按编译器判断而不是按生成器：用 Ninja 驱动 MSVC 也很常见，那时生成器名里
# 并没有 "Visual Studio"，却仍然需要 /MT 与 MSVC 的链接选项。
if (MSVC)
	set(CMAKE_FIND_LIBRARY_SUFFIXES ".lib")
	target_compile_options(PyStand
		PUBLIC
		# 源文件是 UTF-8 且含中文注释。不给 /utf-8 的话 MSVC 按系统 ANSI 代码页
		# 解析，GBK 双字节字符的低位可能正好是 0x5C（反斜杠）——出现在行注释末尾
		# 就成了续行符，把下一行也一起吃掉，编译错误还指不到真正的位置。
		/utf-8
		$<$<CONFIG:Debug>:/MTd>
		$<$<CONFIG:Release>:/MT>
		$<$<CONFIG:MinSizeRel>:/MT>
		)
	target_link_options(PyStand PUBLIC /INCREMENTAL:NO /NODEFAULTLIB:MSVCRT /MANIFEST:NO)
else()
	# for mingw
	set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS_RELEASE} -s")
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS_RELEASE} -s")
	target_link_libraries(PyStand
		-static
		shlwapi
		winmm
		bcrypt
		)
endif()



