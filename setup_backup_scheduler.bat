@echo off
REM Setup automatico para agendar backups diarios do ELEVA
REM Este script configura o Windows Task Scheduler para rodar backup_db.py todo dia

setlocal enabledelayedexpansion

echo.
echo ========================================
echo ELEVA - Setup Agendador de Backup
echo ========================================
echo.

REM Definir variaveis
set SCRIPT_PATH=%CD%\backup_db.py
set TASK_NAME=ELEVA-Backup-Database

echo Criando tarefa agendada: %TASK_NAME%
echo Caminho do script: %SCRIPT_PATH%
echo.

REM Criar tarefa para rodar todo dia as 23:00 (11 PM)
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "python \"%SCRIPT_PATH%\"" ^
  /sc daily ^
  /st 23:00 ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo SUCCESS! ✅
    echo ========================================
    echo.
    echo Tarefa agendada com sucesso!
    echo Nome: %TASK_NAME%
    echo Horario: 23:00 (11:00 PM) todos os dias
    echo.
    echo O banco de dados sera copiado automaticamente para a pasta 'backups\'
    echo.
    echo Para verificar a tarefa, abra:
    echo   Agendador de Tarefas ^(Task Scheduler^)
    echo   Procure por: "%TASK_NAME%"
    echo.
) else (
    echo.
    echo ========================================
    echo ERRO! ❌
    echo ========================================
    echo.
    echo Falha ao criar a tarefa.
    echo Certifique-se de rodar este arquivo como ADMINISTRADOR!
    echo.
)

pause
