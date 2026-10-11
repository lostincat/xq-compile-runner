# XQ 簽章檢查與驗收工具

MIT 授權。這是獨立的驗收入口，不會部署或替換既有常駐執行器或 Open WebUI。沒有模型相依、網路搜尋或下載功能；沒有更動 Windows 安全設定。

## 目前狀態

簽署資格等待審核，沒有受核准的發行者憑證或簽署檔案雜湊。`release.example.json` 故意為空。所有真正桌面案例均為 **NOT_RUN（未執行／未通過驗收）**。隔離測試成功不代表 XQ 通過。

## 一鍵隔離回歸

在這個資料夾執行（Python 3.9+；鎖定測試需要 Windows）：

```powershell
python run_regression.py --output simulated-result-new.json
python acceptance.py --output desktop-plan-new
```

第一個命令只執行 mock 及本機檔案鎖測試。第二個命令預設只建立桌面驗收計畫，退出碼 2 表示未完成，沒有桌面操作。結果檔或資料夾已存在時拒絕覆寫。退出碼 1 為 FAIL；單項桌面測試通過仍為 INCOMPLETE，不會把整套測試標為通過。

## 簽署核准後才設定

複製 `release.example.json` 成本機的 release JSON，由維護者從已核准的正式發布資訊填入 release_id、**簽署後** EXE 的 SHA-256、完整 signer_subject 與 signer_thumbprint。不得直接信任待測 EXE 自報的發行者或把本機未簽署產物當核准版本；憑證輪替需人工重新核准。這份清單是本機信任設定，必須由維護者保管，不能讓模型修改。

```powershell
python signature_gate.py SIGNED_EXE APPROVED_RELEASE_JSON
```

入口用 Windows Get-AuthenticodeSignature 唯讀驗證 Valid 狀態、時間戳簽署憑證存在、精確發行者／憑證指紋及檔案雜湊。它不執行 EXE、不新增信任憑證、不使用 ExecutionPolicy Bypass。檢查脚本若被安全原則阻止，仍回報失敗。此檢查不宣稱 SAC 一定允許執行，亦不提供時間戳完整詳細診斷；正式發行還應由 Microsoft SignTool `verify /pa /all /tw` 驗證，警告亦須人工處理。

參考：https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-authenticodesignature
參考：https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool

## 人工安排的桌面案例

專用文件固定為 `OSS_CompileProbe`，只能是手動建立、可丟棄的測試文件，不可把現有策略改成此名稱。設定檔沿用公開專案的 xq_executable。操作前人工確認 XQ 沒有啟動自動交易；每次只跑一題，過程不要操作剪貼簿或編輯器。

```powershell
python acceptance.py --execute --case normal --confirm-disposable-target OSS_CompileProbe --executable SIGNED_EXE --config LOCAL_CONFIG --release APPROVED_RELEASE_JSON --output runs/new-case
```

可選 normal、syntax_error、wrong_window、popup、unsaved、deadline。先看預設計畫的 setup，再手動安排環境。工具不開啟／關閉彈窗、不觸碰交易或回測按鈕。成功、故意語法錯誤只使用無下單指令的診斷片段。負向案例需吻合指定錯誤才能算「案例通過」；例如簽章失敗不能冒充彈窗防呆通過。視窗／彈窗／未儲存案例還要求空 trace，證明未開始寫入。

deadline 使用一秒期限，但不保證每次觸發；若正常完成，該期限案例標 FAIL，不能冒稱逾時測試成功。55 秒 host watchdog、剪貼簿競爭及中斷保護目前僅有模擬／隔離測試，實際環境故障注入需後續另行安排。

## 邊界與資料保護

- 新入口以同資料夾的 Windows 鎖拒絕第二個工作；不同工具副本或舊執行器不共享此鎖，部署時必須只保留一個有效入口。
- 工作資料夾一旦建立不可重用；中斷留下 claimed.json 時要人工查核，不自動重送。每次正常結束保存 outcome.json；硬終止可能只留下 claimed.json。
- 失敗可能發生在儲存之後，不保證回復；來源備份由原生工具保存，人工檢查。
- 簽章檢查與執行間仍有檔案替換的時間差，應限制發布資料夾的寫入權限。本工具不抵抗同一使用者權限的惡意修改。
- 編譯證據須有新時間戳、精確來源雜湊、單一目標摘要、正確錯誤／警告計數與操作順序。這是保守檢查；多段摘要會直接失敗，待實測後再決定支援方式。
- 執行紀錄含來源、錯誤與本機路徑，不能公開提交；發布只包含審閱過的工具原始碼。

## GitHub Actions

雲端 `Acceptance regression — SIMULATED only` 工作只執行 29 項隔離測試並產生桌面計畫。`SIMULATED` 與 `DESKTOP / NOT_RUN` 分開顯示；沒有 `--execute`，不啟動 XQ 或建置的 EXE。雲端產生的 JSON 報告可從該次工作 artifact 下載；不會上傳本機紀錄或信任清單。
