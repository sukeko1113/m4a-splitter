# m4a Splitter

Windows 向け GUI アプリ。指定した m4a ファイルを、入力した分割数で**均等な長さ**に分割します。

- 再エンコードなし(`ffmpeg -c copy`)で高速・無劣化
- ffmpeg / ffprobe を同梱しているのでエンドユーザーの追加インストール不要
- インストーラー(`.exe`)をダブルクリックするだけで導入完了

> スクリーンショット用プレースホルダ
>
> _(ここにアプリのスクリーンショットを配置)_

---

## エンドユーザー向け: インストールと使い方

1. リリースから `m4a-splitter-setup-X.Y.Z.exe` をダウンロード
2. インストーラーを実行
   - 既定では **管理者権限なし**(ユーザーフォルダ)にインストールされます
   - 「デスクトップにショートカットを作成」を任意で選択可能
3. スタートメニューまたはデスクトップから **m4a Splitter** を起動
4. 操作:
   1. **分割するファイル** で m4a ファイルを選択
   2. **出力フォルダ** を選択(空のままにすると入力ファイルと同じ場所に保存)
   3. **分割数**(2〜999)を指定
   4. **分割実行** ボタンをクリック

出力ファイル名は `<元ファイル名>_part01.m4a`, `_part02.m4a`, ... のように付与されます
(分割数の桁数に応じてゼロ埋め桁数が自動調整されます)。

### アンインストール

Windows の「設定 → アプリ → インストールされているアプリ」から
**m4a Splitter** を選び「アンインストール」してください。

---

## 開発者向け: ビルド手順

ターゲット OS は Windows です。Python 3.10 以上が必要です。

### 1. 依存パッケージのインストール

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. ffmpeg / ffprobe を取得

`bin\` 配下に LGPL ビルドの `ffmpeg.exe` / `ffprobe.exe` が必要です。
以下のスクリプトで自動取得できます:

```powershell
powershell -ExecutionPolicy Bypass -File download_ffmpeg.ps1
```

既定では BtbN の `ffmpeg-master-latest-win64-lgpl-shared.zip` を取得します。
gyan.dev の LGPL ビルドを使いたい場合は `-Url` 引数で URL を差し替えてください。

### 3. exe ビルド(PyInstaller)

```cmd
build.bat
```

`dist\m4a-splitter.exe` が生成されます。

### 4. インストーラー生成(Inno Setup 6)

[Inno Setup 6](https://jrsoftware.org/isdl.php) を事前にインストールしておきます。

```cmd
build_installer.bat
```

`installer\Output\m4a-splitter-setup-1.0.0.exe` が生成されます。

---

## 仕組み

- ffprobe で入力ファイルの総再生時間を取得
- 総時間 ÷ 分割数 を 1 パートあたりの長さとして算出
- ffmpeg を `-ss <start> -t <segment> -c copy` で複数回呼び出し
  - 末尾パートのみ `-t` を付けず EOF まで読むので、丸め誤差の取りこぼしが起きません
- ffmpeg / ffprobe の探索順序:
  1. PyInstaller `--onefile` バンドル内 (`sys._MEIPASS/bin`)
  2. exe と同じフォルダ内の `bin\`
  3. 環境変数 `PATH`

---

## ライセンス

- 本アプリ自体のソースコードは MIT ライセンスで提供します(必要に応じて変更してください)。
- 同梱の `ffmpeg.exe` / `ffprobe.exe` は **LGPL ビルド** であり、その全文は
  `licenses\ffmpeg-LICENSE.txt` を参照してください。
- ffmpeg のソースコードは https://ffmpeg.org/ から入手できます。
