@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
cl /nologo /std:c++17 /EHsc /MD /O2 /I"C:\UE_5.8.0\Engine\Source\ThirdParty\FBX\2020.2\include" Tools\Fbx\audit_bind_pose.cpp /FoSaved\Tools\audit_bind_pose.obj /FeSaved\Tools\audit_bind_pose.exe /link /LIBPATH:"C:\UE_5.8.0\Engine\Source\ThirdParty\FBX\2020.2\lib\vs2017\x64\release" libfbxsdk-md.lib libxml2-md.lib zlib-md.lib wininet.lib ws2_32.lib advapi32.lib
