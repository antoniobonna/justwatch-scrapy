@echo off

:: Create a temporary file
set "tempfile=%TEMP%\git_diff_temp.txt"

:: Write the prefix text to the temp file
(
echo Write a commit message in code without single quotes for this git diff: """
) > "%tempfile%"

:: Append git diff output to the temp file
git diff >> "%tempfile%"

:: Append the suffix to the temp file
(
echo """
) >> "%tempfile%"

:: Copy the contents of the temp file to the clipboard
type "%tempfile%" | clip

:: Clean up
del "%tempfile%"