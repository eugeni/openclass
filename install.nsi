; openclass.nsi
;
; This script installs openclass and adds uninstall support
; and (optionally) installs start menu shortcuts.

;--------------------------------

; The name of the installer
Name "OpenClass"

; The file to write
OutFile "openclass.exe"

; The default installation directory
InstallDir $PROGRAMFILES\OpenClass

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\OpenClass" "Install_Dir"

; Request application privileges for Windows Vista
RequestExecutionLevel admin

;--------------------------------

; Pages

Page components
Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

;--------------------------------

 
Section "Microsoft Visual C++ 2008 Redistributable (required)" SEC01
  SectionIn RO
  
  SetOutPath $INSTDIR

  ; please download it and make available for the installer
  ; available at http://www.microsoft.com/downloads/details.aspx?FamilyID=9b2da534-3e03-4391-8a4d-074b9f2bc1bf&displaylang=en
  File "vcredist_x86.exe"
  ExecWait "$INSTDIR\vcredist_x86.exe"
SectionEnd

; The stuff to install
Section "OpenClass (required)"

  SectionIn RO
  
  ; Set output path to the installation directory.
  SetOutPath $INSTDIR
  
  ; Put file there
  File "win_dist\*.dll"
  File /r "win_dist\iface"
  File "win_dist\lib.dat"
  File "win_dist\*.pyd"
  File "win_dist\teacher.exe"
  File "win_dist\student.exe"
  
  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\NSIS_OpenClass "Install_Dir" "$INSTDIR"
  
  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenClass" "DisplayName" "OpenClass"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenClass" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenClass" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenClass" "NoRepair" 1
  WriteUninstaller "uninstall.exe"
  
SectionEnd

; Optional section (can be disabled by the user)
Section "Start Menu Shortcuts"

  CreateDirectory "$SMPROGRAMS\OpenClass"
  CreateShortCut "$SMPROGRAMS\OpenClass\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  CreateShortCut "$SMPROGRAMS\OpenClass\Teacher.lnk" "$INSTDIR\teacher.exe" "" "$INSTDIR\teacher.exe" 0
  CreateShortCut "$SMPROGRAMS\OpenClass\Student.lnk" "$INSTDIR\student.exe" "" "$INSTDIR\student.exe" 0
  
SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenClass"
  DeleteRegKey HKLM SOFTWARE\NSIS_OpenClass

  ; Remove files and uninstaller
  Delete $INSTDIR\teacher.exe
  Delete $INSTDIR\student.exe
  Delete $INSTDIR\*.dll
  Delete $INSTDIR\*.pyd
  Delete $INSTDIR\lib.dat
  Delete $INSTDIR\uninstall.exe
  Delete "$INSTDIR\vcredist_x86.exe"
  RmDir /r $INSTDIR\iface


  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\OpenClass\*.*"

  ; Remove directories used
  RMDir "$SMPROGRAMS\OpenClass"
  RMDir "$INSTDIR"

SectionEnd

