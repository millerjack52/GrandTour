// Optional diagnostic for our owned editor smoke process only. It records AV
// addresses without handling the exception or changing the real process result.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <cstdio>
#include <cstring>

static const wchar_t* LogPath=L"C:\\GrandTour\\Art\\Export\\MudRoad\\NativeStage4\\exit-probe.txt";
static volatile LONG Observing=0;
static void Write(HANDLE File,const char* Text) { DWORD Done;WriteFile(File,Text,DWORD(strlen(Text)),&Done,nullptr); }
static void Address(HANDLE File,ULONG_PTR A)
{
    HMODULE Module=nullptr;wchar_t Path[1024]={};char Line[2300];
    if(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(A),&Module))
    {
        GetModuleFileNameW(Module,Path,1024);
        sprintf_s(Line,"%p %p +%llx %ls\r\n",reinterpret_cast<void*>(A),Module,static_cast<unsigned long long>(A-reinterpret_cast<ULONG_PTR>(Module)),Path);
    }
    else sprintf_s(Line,"%p unmapped\r\n",reinterpret_cast<void*>(A));
    Write(File,Line);
}
static LONG CALLBACK Observe(EXCEPTION_POINTERS* E)
{
    if(E->ExceptionRecord->ExceptionCode!=EXCEPTION_ACCESS_VIOLATION)return EXCEPTION_CONTINUE_SEARCH;
    if(InterlockedCompareExchange(&Observing,1,0)!=0)return EXCEPTION_CONTINUE_SEARCH;
    HANDLE File=CreateFileW(LogPath,FILE_APPEND_DATA,FILE_SHARE_READ,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(File==INVALID_HANDLE_VALUE){InterlockedExchange(&Observing,0);return EXCEPTION_CONTINUE_SEARCH;}
    char Line[256];sprintf_s(Line,"AV thread=%lu operation=%llu target=%p\r\n",GetCurrentThreadId(),static_cast<unsigned long long>(E->ExceptionRecord->ExceptionInformation[0]),reinterpret_cast<void*>(E->ExceptionRecord->ExceptionInformation[1]));Write(File,Line);
    Address(File,E->ContextRecord->Rip);Write(File,"Unwound stack:\r\n");
    __try
    {
        CONTEXT Context=*E->ContextRecord;
        for(int I=0;I<128 && Context.Rip;++I)
        {
            Address(File,Context.Rip);DWORD64 Base=0,Frame=0;PVOID Data=nullptr;
            const auto Entry=RtlLookupFunctionEntry(Context.Rip,&Base,nullptr);
            if(Entry)RtlVirtualUnwind(UNW_FLAG_NHANDLER,Base,Context.Rip,Entry,&Context,&Data,&Frame,nullptr);
            else {Context.Rip=*reinterpret_cast<DWORD64*>(Context.Rsp);Context.Rsp+=8;}
        }
    }
    __except(EXCEPTION_EXECUTE_HANDLER){}
    Write(File,"Stack candidates (not an unwound call stack):\r\n");
    __try
    {
        const auto* Stack=reinterpret_cast<const ULONG_PTR*>(E->ContextRecord->Rsp);
        for(int I=0;I<256;++I)
        {
            if(Stack[I]>0xffff)Address(File,Stack[I]);
        }
    }
    __except(EXCEPTION_EXECUTE_HANDLER){}
    FlushFileBuffers(File);CloseHandle(File);InterlockedExchange(&Observing,0);return EXCEPTION_CONTINUE_SEARCH;
}
extern "C" __declspec(dllexport) void Install()
{
    HMODULE Module=nullptr;GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&Install),&Module);
    HANDLE File=CreateFileW(LogPath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(File!=INVALID_HANDLE_VALUE)
    {
        Write(File,"Owned smoke process AV observer installed. Modules before teardown:\r\n");
        HANDLE Snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE,GetCurrentProcessId());MODULEENTRY32W M={};M.dwSize=sizeof(M);
        if(Snapshot!=INVALID_HANDLE_VALUE)
        {
            if(Module32FirstW(Snapshot,&M))do
            {
                char Line[2300];sprintf_s(Line,"MODULE %p %lu %ls\r\n",M.modBaseAddr,M.modBaseSize,M.szExePath);Write(File,Line);
            }while(Module32NextW(Snapshot,&M));
            CloseHandle(Snapshot);
        }
        CloseHandle(File);
    }
    AddVectoredExceptionHandler(1,Observe);
}
