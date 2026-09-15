@echo off
REM Minimal tee: pipes raw stdin bytes to the console and to the file given as %1.
REM Usage: some_command 2^>^&1 ^| scripts\tee.bat logs\xxx.log
REM The file is truncated each run, so every start-dev gets a clean console log.
REM Bytes are passed through without decoding or re-encoding, so the file holds the
REM process output verbatim (usually UTF-8). Letting PowerShell decode by console
REM codepage would corrupt non-ASCII output or emit UTF-16.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$in=[Console]::OpenStandardInput(); $out=[Console]::OpenStandardOutput(); $fs=[IO.File]::Create('%~1');" ^
  "$buf=New-Object byte[] 8192;" ^
  "try{ while(($n=$in.Read($buf,0,$buf.Length)) -gt 0){ $out.Write($buf,0,$n); $out.Flush(); $fs.Write($buf,0,$n); $fs.Flush() } } finally { $fs.Close() }"
