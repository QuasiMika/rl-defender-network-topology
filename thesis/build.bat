@echo off
REM =====================================================================
REM  Perl-freier Build der Bachelorarbeit (ohne latexmk).
REM  In WINDOWS PowerShell/cmd (NICHT im WSL-Terminal) ausfuehren:
REM      .\build.bat
REM  Nutzt nur pdflatex.exe und biber.exe (beide brauchen KEIN Perl).
REM  pushd mappt UNC-Pfade (\\wsl.localhost\...) auf ein temp. Laufwerk,
REM  damit der Build auch aus dem WSL-Dateisystem heraus funktioniert.
REM =====================================================================
pushd "%~dp0"

echo [1/4] pdflatex...
pdflatex -interaction=nonstopmode thesis.tex || goto :error
echo [2/4] biber...
biber thesis || goto :error
echo [3/4] pdflatex...
pdflatex -interaction=nonstopmode thesis.tex || goto :error
echo [4/4] pdflatex...
pdflatex -interaction=nonstopmode thesis.tex || goto :error

echo.
echo Fertig: thesis.pdf
popd
goto :eof

:error
echo.
echo Build fehlgeschlagen - siehe thesis.log
popd
exit /b 1
