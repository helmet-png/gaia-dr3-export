# -*- coding: utf-8 -*-
"""Gaia DR3 資料擷取工具 — 本地後端
純 Python 標準庫實作，透過 ESA Gaia Archive TAP API 查詢 gaiadr3.gaia_source。
啟動：py server.py  →  http://localhost:8777
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("GAIA_PORT", "8777"))
TAP_SYNC_URL = "https://gea.esac.esa.int/tap-server/tap/sync"
# 名稱解析（CDS Sesame）— 用純 HTTP 避開本機 CDS 憑證驗證問題；主站失敗則試 Harvard 鏡像
SESAME_URLS = (
    "http://cds.unistra.fr/cgi-bin/nph-sesame/-oI/SNV?{q}",
    "http://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oI/SNV?{q}",
)
DEFAULT_OUTDIR = str(Path.home() / "Documents" / "GaiaExports")
# 打包成 exe（PyInstaller）時靜態檔被解壓到 sys._MEIPASS；一般執行則用原始碼目錄
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))

# 已匯出檔案登記表：id -> 絕對路徑（供 /api/download 下載）
EXPORTS: dict[str, str] = {}

COLUMN_RE = re.compile(r"^[a-z_][a-z0-9_]*$", re.IGNORECASE)


def build_where(params: dict) -> str:
    """把查詢參數組成 ADQL 的 WHERE 條件（供 build_adql 與 count 共用）"""
    where = []
    mode = params.get("mode", "cone")
    if mode == "cone":
        ra = float(params["ra"])
        dec = float(params["dec"])
        radius = float(params["radius"])
        where.append(
            "1=CONTAINS(POINT('ICRS', ra, dec), "
            f"CIRCLE('ICRS', {ra}, {dec}, {radius}))"
        )
    elif mode == "box":
        ra_min, ra_max = float(params["ra_min"]), float(params["ra_max"])
        dec_min, dec_max = float(params["dec_min"]), float(params["dec_max"])
        where.append(f"ra BETWEEN {ra_min} AND {ra_max}")
        where.append(f"dec BETWEEN {dec_min} AND {dec_max}")
    else:
        raise ValueError(f"未知的查詢模式: {mode}")

    if params.get("mag_max") not in (None, ""):
        where.append(f"phot_g_mean_mag <= {float(params['mag_max'])}")
    if params.get("parallax_min") not in (None, ""):
        where.append(f"parallax >= {float(params['parallax_min'])}")
    return " AND ".join(where)


def build_adql(params: dict, top: int) -> str:
    cols = params.get("columns") or ["source_id", "ra", "dec"]
    for c in cols:
        if not COLUMN_RE.match(c):
            raise ValueError(f"不合法的欄位名稱: {c}")
    return (
        f"SELECT TOP {top} {', '.join(cols)} "
        f"FROM gaiadr3.gaia_source WHERE {build_where(params)}"
    )


def count_sources(params: dict) -> int:
    """回傳符合目前範圍/篩選條件的總星數（給「全部抓取」用）"""
    adql = f"SELECT COUNT(*) AS n FROM gaiadr3.gaia_source WHERE {build_where(params)}"
    raw = run_tap_query(adql, "json").decode("utf-8", "replace")
    return int(json.loads(raw)["data"][0][0])


def resolve_name(name: str) -> tuple[float, float]:
    """用 CDS Sesame 把天體名稱解析成 (ra, dec) 十進位度數"""
    q = urllib.parse.quote(name.strip())
    last = "未知錯誤"
    for tmpl in SESAME_URLS:
        try:
            req = urllib.request.Request(
                tmpl.format(q=q), headers={"User-Agent": "gaia-export-tool/1.0"})
            txt = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            for line in txt.splitlines():
                if line.startswith("%J "):
                    parts = line.split()
                    return float(parts[1]), float(parts[2])
            last = "服務未回傳座標（可能查無此天體）"
        except Exception as e:  # noqa: BLE001
            last = str(e)
    raise ValueError(f"無法解析「{name}」：{last}")


def run_tap_query(adql: str, fmt: str) -> bytes:
    data = urllib.parse.urlencode({
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "FORMAT": fmt,
        "QUERY": adql,
    }).encode()
    req = urllib.request.Request(TAP_SYNC_URL, data=data, headers={
        "User-Agent": "gaia-export-tool/1.0",
    })
    with urllib.request.urlopen(req, timeout=600) as resp:
        return resp.read()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # pythonw（無主控台）模式下 stderr 為 None，寫入會中斷連線
        if sys.stderr:
            sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    # ---------- helpers ----------
    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    # ---------- GET ----------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            page = (BASE_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif parsed.path == "/gaia_columns.js":
            js = (BASE_DIR / "gaia_columns.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(js)))
            self.end_headers()
            self.wfile.write(js)
        elif parsed.path == "/api/defaults":
            self.send_json({"outdir": DEFAULT_OUTDIR})
        elif parsed.path == "/api/download":
            qs = urllib.parse.parse_qs(parsed.query)
            file_id = (qs.get("id") or [""])[0]
            path = EXPORTS.get(file_id)
            if not path or not os.path.isfile(path):
                self.send_json({"error": "找不到檔案"}, 404)
                return
            data = Path(path).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(path)}"',
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_json({"error": "not found"}, 404)

    # ---------- POST ----------
    def do_POST(self):
        try:
            if self.path == "/api/preview":
                self.handle_preview()
            elif self.path == "/api/export":
                self.handle_export()
            elif self.path == "/api/resolve":
                self.handle_resolve()
            elif self.path == "/api/count":
                self.handle_count()
            elif self.path == "/api/open-folder":
                self.handle_open_folder()
            elif self.path == "/api/pick-folder":
                self.handle_pick_folder()
            else:
                self.send_json({"error": "not found"}, 404)
        except (ValueError, KeyError) as e:
            self.send_json({"error": f"參數錯誤：{e}"}, 400)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            self.send_json({"error": f"Gaia TAP 服務回傳錯誤 (HTTP {e.code})：{detail}"}, 502)
        except urllib.error.URLError as e:
            self.send_json({"error": f"無法連線 Gaia Archive：{e.reason}"}, 502)
        except Exception as e:  # noqa: BLE001
            self.send_json({"error": f"伺服器錯誤：{e}"}, 500)

    def handle_preview(self):
        params = self.read_body()
        adql = build_adql(params, top=20)
        raw = run_tap_query(adql, "json").decode("utf-8", "replace")
        result = json.loads(raw)
        self.send_json({
            "adql": adql,
            "columns": [m["name"] for m in result.get("metadata", [])],
            "rows": result.get("data", []),
        })

    def handle_resolve(self):
        params = self.read_body()
        ra, dec = resolve_name(params.get("name", ""))
        self.send_json({"ra": ra, "dec": dec})

    def handle_count(self):
        params = self.read_body()
        self.send_json({"count": count_sources(params)})

    def handle_export(self):
        params = self.read_body()
        if params.get("grab_all"):
            # 全部抓取：先數總星數，再以該數量為列數上限，確保不被截斷
            top = min(count_sources(params), 3_000_000)
        else:
            top = min(int(params.get("limit") or 10000), 3_000_000)
        fmt = params.get("format", "csv")
        if fmt not in ("csv", "votable", "json"):
            raise ValueError(f"不支援的格式: {fmt}")
        adql = build_adql(params, top=top)

        outdir = Path(params.get("outdir") or DEFAULT_OUTDIR).expanduser()
        outdir.mkdir(parents=True, exist_ok=True)
        ext = {"csv": "csv", "votable": "xml", "json": "json"}[fmt]
        filename = f"gaia_dr3_{time.strftime('%Y%m%d_%H%M%S')}.{ext}"
        path = outdir / filename

        data = run_tap_query(adql, fmt)
        path.write_bytes(data)

        rows = None
        if fmt == "csv":
            rows = max(data.count(b"\n") - 1, 0)  # 扣除標題列

        file_id = f"f{len(EXPORTS)}_{int(time.time())}"
        EXPORTS[file_id] = str(path)
        self.send_json({
            "path": str(path),
            "adql": adql,
            "rows": rows,
            "bytes": len(data),
            "download_id": file_id,
        })

    def handle_open_folder(self):
        params = self.read_body()
        path = params.get("path", "")
        if not os.path.exists(path):
            raise ValueError(f"路徑不存在: {path}")
        if os.path.isfile(path):
            # 開啟檔案總管並選取該檔案
            subprocess.Popen(["explorer", f"/select,{path}"])
        else:
            subprocess.Popen(["explorer", path])
        self.send_json({"ok": True})

    def handle_pick_folder(self):
        # 用獨立子行程開 tkinter 資料夾選擇對話框，避免執行緒衝突
        code = (
            "import tkinter, tkinter.filedialog;"
            "r=tkinter.Tk();r.withdraw();r.attributes('-topmost',True);"
            "print(tkinter.filedialog.askdirectory() or '')"
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=300,
        )
        folder = out.stdout.strip().replace("/", "\\")
        self.send_json({"folder": folder})


class Server(ThreadingHTTPServer):
    # Windows 上 SO_REUSEADDR 會允許重複綁定同一埠，關閉它讓第二份實例確實拿到 OSError
    allow_reuse_address = False


if __name__ == "__main__":
    try:
        server = Server(("127.0.0.1", PORT), Handler)
    except OSError:
        # 埠已被占用 = 伺服器已在執行中，安靜退出（供桌面捷徑重複點擊）
        sys.exit(0)
    if sys.stdout:
        print(f"Gaia DR3 匯出工具已啟動：http://localhost:{PORT}")
    server.serve_forever()
