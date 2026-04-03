; ============================================================
; TZH Promet vs Banka — One-Click NSIS Installer
; ============================================================
; Build: makensis installer.nsi
; Requires: NSIS 3.x (https://nsis.sourceforge.io)
; Input:  dist\TZH-Promet-vs-Banka\ (PyInstaller output)
; Output: TZH-Promet-vs-Banka-Setup-x.x.x.exe
; ============================================================
; User experience: double-click → progress bar → app launches
; No wizard, no questions, no admin required (installs to AppData)
; ============================================================

!include "MUI2.nsh"
!include "FileFunc.nsh"

; --- App metadata ---
!define APP_NAME      "TZH Promet vs Banka"
!define APP_EXE       "TZH-Promet-vs-Banka.exe"
!define APP_PUBLISHER "Tvornica Zdrave Hrane"
!define APP_URL       "https://tvornicazdravehrane.hr"
!define DIST_DIR      "dist\TZH-Promet-vs-Banka"

; Read version from version.py at compile time
!searchparse /file "version.py" `__version__ = "` APP_VERSION `"`

Name "${APP_NAME}"
OutFile "TZH-Promet-vs-Banka-Setup-${APP_VERSION}.exe"
Caption "Instaliranje ${APP_NAME} v${APP_VERSION}..."

; Install to AppData — no admin privileges needed
InstallDir "$LOCALAPPDATA\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel user

SetCompressor /SOLID lzma

; --- MUI Configuration ---
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"

; Show progress bar with file details
ShowInstDetails show

; Only show the progress page — no welcome, no directory picker
!define MUI_INSTFILESPAGE_COLORS "FFFFFF 000000"
!insertmacro MUI_PAGE_INSTFILES

; Finish page — show "Launch app" checkbox
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Pokreni ${APP_NAME}"
!define MUI_FINISHPAGE_TITLE "Instalacija zavrsena!"
!define MUI_FINISHPAGE_TEXT "${APP_NAME} v${APP_VERSION} je uspjesno instaliran.$\r$\n$\r$\nKliknite Zavrsi za pokretanje aplikacije."
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; --- Language ---
!insertmacro MUI_LANGUAGE "Croatian"

; ============================================================
; On Init — check if already running
; ============================================================
Function .onInit
    FindWindow $0 "" "${APP_NAME}"
    ${If} $0 != 0
        MessageBox MB_OKCANCEL|MB_ICONINFORMATION \
            "${APP_NAME} je trenutno pokrenut.$\r$\n$\r$\nKliknite OK za zatvaranje i nastavak instalacije." \
            IDOK close_app
        Abort
        close_app:
            SendMessage $0 ${WM_CLOSE} 0 0
            Sleep 2000
    ${EndIf}
FunctionEnd

; ============================================================
; Install Section
; ============================================================
Section "Install"
    SetOutPath "$INSTDIR"
    DetailPrint "Kopiram datoteke..."

    ; Copy all files from PyInstaller dist
    File /r "${DIST_DIR}\*.*"

    ; Copy icon
    File "assets\icon.ico"

    DetailPrint "Kreiram precice..."

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; --- Start Menu shortcut ---
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\icon.ico" 0
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Deinstaliraj.lnk" \
        "$INSTDIR\Uninstall.exe"

    ; --- Desktop shortcut ---
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\icon.ico" 0

    DetailPrint "Registriram aplikaciju..."

    ; --- Registry: Add/Remove Programs (per-user) ---
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayIcon" "$INSTDIR\icon.ico"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "NoRepair" 1

    ; Calculate installed size for Add/Remove Programs
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "EstimatedSize" $0

    ; Save install dir
    WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\${APP_NAME}" "Version" "${APP_VERSION}"

    DetailPrint "Instalacija zavrsena!"
SectionEnd

; ============================================================
; Uninstall Section
; ============================================================
Section "Uninstall"
    ; Force-kill all running instances (prevents zombie processes)
    ExecWait 'taskkill /F /IM "${APP_EXE}" /T' $0
    Sleep 1000

    ; Remove all installed files
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\${APP_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\${APP_NAME}"

    ; Remove registry entries
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd

; ============================================================
; Uninstaller init — confirm dialog
; ============================================================
Function un.onInit
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Zelite li deinstalirati ${APP_NAME}?" \
        IDYES +2
    Abort
FunctionEnd
