param([Parameter(Mandatory)][Diagnostics.Process]$GameProcess)
$GameProcess.Refresh()
if($GameProcess.HasExited -or $GameProcess.MainWindowHandle -eq [IntPtr]::Zero){return $false}
if(!('GrandTour.BenchmarkWindow' -as [type])){
 Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

namespace GrandTour {
    public static class BenchmarkWindow {
        [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window, out uint process);
        [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
        [DllImport("user32.dll")] static extern bool AttachThreadInput(uint a, uint b, bool attach);
        [DllImport("user32.dll")] static extern bool BringWindowToTop(IntPtr window);
        [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);

        public static bool Activate(IntPtr window, uint gameProcess) {
            uint pid;
            uint target = GetWindowThreadProcessId(window, out pid);
            if (target == 0 || pid != gameProcess) return false;
            uint front = GetWindowThreadProcessId(GetForegroundWindow(), out pid);
            if (pid == gameProcess) return true;
            uint caller = GetCurrentThreadId();
            bool joinedFront = front != 0 && front != caller && AttachThreadInput(caller, front, true);
            bool joinedGame = target != caller && target != front && AttachThreadInput(caller, target, true);
            try {
                BringWindowToTop(window);
                SetForegroundWindow(window);
                GetWindowThreadProcessId(GetForegroundWindow(), out pid);
                return pid == gameProcess;
            } finally {
                if (joinedGame) AttachThreadInput(caller, target, false);
                if (joinedFront) AttachThreadInput(caller, front, false);
            }
        }
    }
}
'@
}
[GrandTour.BenchmarkWindow]::Activate($GameProcess.MainWindowHandle,$GameProcess.Id)
