# MGS Peace Walker（Master Collection）繁體中文化

目前版本：**Beta 0.1**（測試階段）

非官方的玩家自製繁體中文化，以日文版為翻譯來源，適用於 Steam 的《METAL GEAR SOLID: PEACE WALKER》（Master Collection 版）。

## 中文化內容
- 遊戲內文字（選單、任務、劇情字幕、簡報錄音帶、道具與武器說明等）。
- 字型：新增繁體字形，標點採台灣式全形置中。
- 圖片：前情提要、章節標題、Boss 與載具登場標題卡、開頭法律頁、教學截圖。
- 影片（選用）：5 支文字卡影片的字幕。
- 未翻譯：動態漫畫（ADEMO）的英文對話框、廣告圖、KEY HELP 說明書頁面。

## 安裝需求
- 自備正版遊戲（Steam）。
- 日文語言包：本漢化包以日文版為基礎，**需自行取得日文語言包**（本專案不提供來源）。安裝程式會偵測遊戲資料夾是否已裝；沒有的話，可指定你自己的日文包資料夾，由安裝程式複製缺少的檔案。
- 影片中文化（選用）：需自備 ffmpeg（含 libx264 與 libass）；安裝程式不下載、不內附。
- 強烈建議另外安裝 [MGSPatriotFix](https://www.nexusmods.com/metalgearsolidpeacewalkermc/mods/1)（不內附）。

## 安裝
Windows：執行安裝程式，依畫面步驟（免責聲明 → 選擇遊戲資料夾 → 日文包 → 影片選項 → 安裝）。
命令列：`python zhtw_installer.py --cli`（`--auto` 為代勞模式，Linux／SteamOS 預設開啟；可加 `--game` 資料夾、`--jppack` 日文包資料夾、`--ffmpeg` 路徑、`--accept` 表示同意免責聲明；動作為 `install`、`remove`、`remove-all`、`status`）。
SteamOS（Steam Deck）：請看 [SteamOS教學.md](SteamOS教學.md)（手把手教你進入桌面模式、開終端機、執行 `steamos_install.sh`；安裝程式有「代勞模式」，會自動找遊戲資料夾、日文包與 ffmpeg；**未經實機測試**）。

## 移除與還原
再次執行安裝程式，選擇「只移除漢化包」（還原被取代的原檔）或「移除漢化包與日文包」（日文包只移除由本程式複製的檔案）。安裝程式會在動手前驗證原檔雜湊，不符就整批拒絕，不會留下半完成的檔案。
也可以用 Steam「驗證遊戲檔案完整性」還原遊戲檔案。

## 回報問題
請至 [GitHub Issues](https://github.com/BarretShellBear/MGS-PW-ZHTW/issues) 回報，並附上**版本號**（也記錄在遊戲資料夾的 `zhtw_version.txt`）、平台與設備、問題類型、發生位置、描述與截圖。SteamOS 另請註明設備型號與 SteamOS 版本。

## 版本沿革
見 [CHANGELOG.txt](CHANGELOG.txt)。

## 免責聲明
1. 本漢化包為非官方的玩家自製作品，與 Konami 及任何版權方無關。
2. 本漢化包不含遊戲本體，也不含日文語言包。
3. 安裝前請自行備份存檔；製作者對任何資料損失、遊戲無法執行或其他後果不負責任。
4. 禁止商用，禁止轉售。
5. 遊戲內容與商標的著作權屬於原權利人。
6. 請自行確認所在地區的法律是否允許使用。
7. 目前為測試階段，翻譯可能不完整或有缺字漏字，歡迎回報；收到回報後會修正並釋出新版本。
8. （SteamOS 版）製作者沒有 SteamOS 設備，SteamOS 版只是順便製作；若發現重大執行瑕疵，將中止 SteamOS 版的更新。

## 授權與致謝
檔案格式處理程式碼來自下列 MIT 授權專案，授權全文見 [licenses/](licenses/)：Peace Walker Localization Tool（Little Bit Team）、pwtr。
在此一併致上感謝：MGS4-ZHTW（github.com/DickleDD/MGS4-ZHTW）、GzsTool／FoxEngine.TranslationTool（github.com/Atvaark）、MGSPatriotFix、Noto 字型（Google Fonts）、MGS Delta 與 MGS5 的官方繁體中文譯名資料。
本包不內附 Noto 字型檔，只含字型已寫入遊戲字型檔的字形。

## 下載
到 [Releases](https://github.com/BarretShellBear/MGS-PW-ZHTW/releases) 下載最新版的 zip，解壓縮後依上面的說明安裝。

## 這個倉庫裡有什麼
- `installer/`：安裝程式原始碼、說明與 SteamOS 教學（安裝包本體在 Releases）
- `translate/`：用語對照表、翻譯規範，以及最終的繁體中文譯文表（只有中文，不含日文原文）
- `.github/ISSUE_TEMPLATE/`：問題回報範本
