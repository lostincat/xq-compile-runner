# XQ Compile Runner

Experimental, MIT-licensed Windows desktop compile runner. Maintained by [lostincat](https://github.com/lostincat). This project is not affiliated with XQ or its vendor.

**Unsigned experimental release. Desktop acceptance for this version has NOT RUN.** Do not disable Smart App Control to run it. See the [Code signing policy](CODE_SIGNING.md).

這是一個獨立的 Windows 使用者桌面工具，在使用者自行開啟的 XScript 編輯器中，僅對專用交易類型測試文件 `OSS_CompileProbe` 貼入來源、存檔、編譯並讀取錯誤。它不建立文件、不關閉彈窗、不操作回測或下單。貼入內容由呼叫者提供；本工具不是策略安全性或獲利能力檢查器。

**候選版未通過桌面驗收，不能當成已可用的無人值守工具。** Windows 智慧型應用程式控制維持開啟；建置不會執行或簽署產物。不得利用本專案繞過被封鎖的二進位程式。

## 範圍

- `src/Desktop.cs`：C# 桌面編譯核心，使用 Windows UI Automation 與 Scintilla 訊息。
- `runner.py`：單筆工作呼叫器，55 秒程序期限，失敗不重試。
- `tests/`：隔離測試，所有程序啟動均為 mock；不呼叫 XQ。
- `docs/`：介面、安全、隱私、來源及人工驗收说明。

公開候選包不含 XQ 程式、交易策略、知識庫、帳號資料、原始執行紀錄、二進位檔或本機部署設定。既有私人 Open WebUI 佇列、常駐服務及其部署程式刻意不打包，因此這不是原系統可直接替換的發布版本。

## 建置與單元測試

需求：Windows x64、.NET Framework 4.x 編譯器及 WPF/UI Automation 參考組件；測試另需 Python 3.9+。無第三方 Python 套件。未提供固定雜湊的可重現建置保證。

在專案資料夾執行：

```powershell
.\Build.ps1
python -m unittest discover -s tests -v
```

產物在 `bin/XqCompileRunner.exe`。若執行原則拒絕建置腳本，循正常管理流程處理；不要設定 ExecutionPolicy Bypass。建置成功不表示 Windows 核准執行。

## 正式簽署並完成審核後的使用方式

1. 複製 `config.example.json` 為 `config.local.json`，將 `xq_executable` 設為實際 `daqxqlite.exe` 絕對路徑；JSON 中反斜線需寫成雙反斜線。設定檔留在本機。
2. 在 XQ 手動建立專用的交易類型文件 `OSS_CompileProbe`，確認沒有既有同名策略。保留單一 XScript 編輯器，儲存測試文件並關閉彈窗。專用文件必須可丟棄，不能改用現有策略名稱。
3. 依 `docs/PROTOCOL.md` 產生本機 request JSON；來源、結果與備份均視為私人資料。
4. 通過簽章與 Windows 執行檢查後，才可執行：

```powershell
python tools/acceptance/runner.py bin/XqCompileRunner.exe config.local.json request.local.json runs/new-unique-job --release APPROVED_RELEASE_JSON
```

呼叫器以 `PASS`／`FAIL` 與退出碼 0／1 表示結果。警告數不為零仍可能編譯成功，呼叫者應另設警告政策。程式不提供排程、開機啟動、網路埠或 Open WebUI 部署；外部系統需先完成自己的認證、佇列、序列化及證據驗證。

詳見 [安全限制](SECURITY.md)、[人工驗收](docs/ACCEPTANCE.md)、[來源說明](docs/PROVENANCE.md)。

## 簽章檢查與分開標示的驗收

請使用 [驗收工具](tools/acceptance/README.md) 作為簽署後的操作入口；根目錄 `runner.py` 是舊版協定範例，沒有新增的簽章入口檢查，不適合直接作為部署入口。雲端新增 29 項隔離測試，與原有 12 項測試分開執行；所有真正桌面案例固定標為 `NOT_RUN`，不因 CI 綠燈視為已驗收。
