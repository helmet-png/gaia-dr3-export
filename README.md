# Gaia DR3 Export Tool

A lightweight, local tool to query and export data from the ESA Gaia DR3 catalogue
(`gaiadr3.gaia_source`) by sky region and column, through a browser-based UI.
Resolve objects by name (e.g. `NGC 6910`), grab an entire region in one click, and
export to CSV / VOTable / JSON on your own machine.

> 繁體中文說明請見下方 [中文說明](#中文說明)。

## Features

- **Cone or box search** — query by centre + radius, or by an RA/Dec box.
- **Name resolution** — type an object name (`NGC 6910`, `M45`, …) and the
  coordinates are filled in automatically via the CDS Sesame resolver. You can
  also paste plain decimal coordinates.
- **Grab all** — one checkbox counts the region and downloads *every* matching
  source, with no row-limit truncation.
- **152 columns** — every `gaia_source` column, searchable, with descriptions
  and units.
- **Local export** — writes CSV / VOTable / JSON to a folder you choose, and can
  open the file location in your file manager.
- **Zero dependencies** — pure Python standard library. No `pip install` needed.

## Requirements

- Python 3.9+ (Windows / macOS / Linux)
- An internet connection (queries the ESA Gaia Archive in real time)

## Run

```bash
python server.py
```

Then open <http://localhost:8777> in your browser.
On Windows you can also double-click `launch_gaia.vbs` to start the server hidden
(no terminal window) and open the browser automatically.

## Usage

1. Under **快速定位 / Quick locate**, type an object name or coordinates and search.
2. Set the search radius, pick the columns you want, optionally add a magnitude or
   parallax filter.
3. Tick **全部抓取 / Grab all** to fetch the whole region, or set a row limit.
4. Click **Export**. The resulting file path is shown and can be opened directly.

## Build a standalone .exe (Windows)

```bash
pip install pyinstaller
pyinstaller --onefile --name GaiaDR3Export ^
  --add-data "index.html;." --add-data "gaia_columns.js;." app.py
```

The single-file `dist/GaiaDR3Export.exe` bundles Python and all assets — the
target machine needs nothing installed.

## How it works

The browser front-end collects your query and posts it to a small local Python
server. The server translates it into ADQL and sends a synchronous query to the
ESA Gaia Archive over the IVOA-standard **TAP** protocol. Results are filtered on
ESA's servers and returned as CSV / VOTable / JSON, then written to your chosen
folder. No copy of the database is stored locally; every query uses the official
public API.

## Data source & attribution

Data: ESA Gaia Archive — `gaiadr3.gaia_source`.
This work has made use of data from the European Space Agency (ESA) mission
[Gaia](https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and
Analysis Consortium (DPAC). Object name resolution uses the CDS
[Sesame](https://cds.unistra.fr/cgi-bin/Sesame) service.

## License

Released under the [MIT License](LICENSE).

---

## 中文說明

一個輕量的本機工具，用瀏覽器介面從 ESA Gaia DR3 星表（`gaiadr3.gaia_source`）
擷取指定天區與欄位的資料。可用星團／天體名稱（如 `NGC 6910`）搜尋、一鍵抓取整個
天區，並匯出 CSV / VOTable / JSON 到本機。

### 功能

- **錐形／矩形天區查詢**：以圓心＋半徑，或 RA/Dec 上下限查詢。
- **名稱解析**：輸入天體名稱自動填入座標（透過 CDS Sesame）；也可直接貼上座標。
- **全部抓取**：自動計算星數並下載全部符合條件的資料，不受列數上限截斷。
- **152 個欄位**：所有 `gaia_source` 欄位可搜尋勾選，含說明與單位。
- **本機匯出**：寫入你指定的資料夾，並可直接開啟檔案位置。
- **零依賴**：純 Python 標準庫，無需安裝任何套件。

### 執行

```bash
python server.py
```

開啟 <http://localhost:8777>。Windows 亦可雙擊 `launch_gaia.vbs` 隱藏啟動並自動
開啟瀏覽器。

### 原理

前端把查詢送到本機 Python 伺服器，伺服器轉成 ADQL，透過 IVOA 標準的 TAP 協定向
ESA Gaia Archive 發出同步查詢；資料在 ESA 端篩選後回傳，寫入你指定的資料夾。全程
使用官方公開 API，不在本機存放資料庫副本。

### 資料來源

資料取自 ESA Gaia Archive（`gaiadr3.gaia_source`）。名稱解析使用 CDS Sesame 服務。
