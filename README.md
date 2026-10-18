# TL;DR
- [Gemini](https://gemini.google.com/app)から生成されたスタイル変換画像を、Ro8arm(ロバームと呼ぶ)で油絵を作成

# Youtube
[![](https://github.com/Bucchiman/Ro8arm_picture/assets/52972710/73a2ddcc-e0c1-44d9-b226-55fcee7e170d)](https://youtu.be/B4mbg4YEaI8?si=o93_vK5WoJgbUO7y)

# 用意するもの
- [６軸ロボットアーム](https://www.amazon.co.jp/DIY-MORE-DiyStudio-6%E8%87%AA%E7%94%B1%E5%BA%A6%E3%83%AD%E3%83%9C%E3%83%83%E3%83%88%E3%82%A2%E3%83%BC%E3%83%A0DIY%E3%82%AD%E3%83%83%E3%83%88%E3%82%A2%E3%83%AB%E3%83%9F%E3%83%A1%E3%82%AB%E3%83%8B%E3%82%AB%E3%83%AB%E3%82%A2%E3%83%BC%E3%83%A0%E3%82%B8%E3%83%A7%E3%83%BCArduinor-MG995%E3%82%B5%E3%83%BC%E3%83%9C%E3%83%89%E3%83%A9%E3%82%A4%E3%83%96%E3%83%90%E3%83%AB%E3%82%AF%EF%BC%88%E7%B5%90%E5%90%88%E3%81%99%E3%82%8B%E5%BF%85%E8%A6%81%E3%81%8C%E3%81%82%E3%82%8A%E3%81%BE%E3%81%99%EF%BC%89%E3%81%AF%E6%97%A5%E6%9C%AC%E8%AA%9E%E3%81%AE%E7%B5%84%E3%81%BF%E7%AB%8B%E3%81%A6%E8%AA%AC%E6%98%8E%E6%9B%B8%E3%82%92%E9%80%81%E3%82%8B%E3%81%93%E3%81%A8%E3%81%8C%E3%81%A7%E3%81%8D%E3%81%BE%E3%81%99/dp/B07M7TK6KR)
- [pca9685](https://www.amazon.co.jp/Jectse-PCA9685/dp/B09JNMS3L2/ref=sr_1_3_sspa?dib=eyJ2IjoiMSJ9.hU05jfSkM1QtMZS8kILVPMiitp7GwbSV_HbUIuKzuzbastQmNjSbwA319jEnsC-eNSobN0IUMB_aSD5hnrhE9qDOFWiDX86gV95NSUuBA_ZpyL-qkZkBMsENBm__q4WdMhDeFEJnTTZDvnhsQo8GlYbSKWx_W1JD5hUbXMPGOKP4dR6OKYw2gwUIMnvFrHkMzNQqT_Cy-XyRihHtt7RyDFFHQA1uuwG_5ozGKXhZSmbATIVtLVj0N-SXNOAvaeNofXYN3xSSem5Bt87euux6Ay0CVBeVjiB2ASF4TgEumWo.GD9CrugmwQBwMSgxlXF29W8DlkPjLjs4eg3Uk_plunA&dib_tag=se&keywords=PCA9685&qid=1709920222&sr=8-3-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1)
- Jetson nano(Raspberry piでも代用可)

# 実行方法
ロボットアームの組み立て、および、回路は[こちら](https://qiita.com/teatime77/items/39f59220cea21c2d3abc)を参照。
```bash
$ git clone git@github.com:Bucchiman/Ro8arm_picture.git
$ cd Ro8arm_picture
$ python -m venv venv
$ pip install opencv-python adafruit_pca9685
$ sudo chmod 777 /dev/i2c-1
$ python ./src/fuji.py
```

# painter（汎用油絵マシン / 開発中）
任意の画像を、複数の筆で人間のような筆運びの油絵にするための新しいパイプライン。
機構は XY ガントリー + Z(筆圧) + 筆回転軸 + ツールチェンジャー（3D プリンタでプロトタイプ予定）、制御は Klipper を想定。
フェーズ1はシミュレータで検証する。旧ロボットアーム版（`src/`）はそのまま残している。

```
入力画像 → 色解析(N色パレット) → ストローク生成(粗い筆→細い筆) → 工程計画(筆替え/洗浄/補充) → PaintProgram(JSON)
                                                                         ├→ シミュレータ（仮想キャンバス・工程動画・レポート）
                                                                         └→ Klipper G-code
```

- 色替え時は必ず「油壺で洗浄 → 布で拭き取り → 新しい色を取る」。筆はラックに戻す前にも洗浄する
- 絵の具が減ったスロットは一時停止（`REFILL_PAUSE`）して人間が補充 → `RESUME`
- 人間が混色すべき色とスロット番号は `palette_sheet.png` に出力

```bash
$ uv venv && uv pip install -e '.[dev]'
$ .venv/bin/painter run date/raw_images/gemini_fuji_04.jpeg -o out/fuji04 --colors 10 --video
#   out/fuji04/palette_sheet.png  パレットに置く色
#   out/fuji04/canvas.png         シミュレーション結果
#   out/fuji04/process.mp4        筆替え・洗浄を含む工程動画
#   out/fuji04/report.json        ストローク数・洗浄回数・推定時間・色別使用量・SSIM/ΔE
#   out/fuji04/program.gcode      Klipper 用 G-code（マクロは klipper/macros.cfg）
$ .venv/bin/pytest
```

### 動きの確認
```bash
# 1本のストロークを拡大表示（XY軌跡・筆の向き・Z押し込み・速度のアニメーション+グラフ）。既定は各筆の最初の1本、4倍スロー
$ .venv/bin/painter inspect out/fuji04/program.json -o out/fuji04/inspect
$ .venv/bin/painter inspect out/fuji04/program.json -o out/fuji04/inspect --stroke 2596 --slow 8

# G-code を Klipper マクロ込みで実行して安全チェック＋再生動画（全工程を60秒に圧縮）
$ .venv/bin/painter gcode-sim out/fuji04/program.gcode -o out/fuji04/gcode_sim --program out/fuji04/program.json --video
# 最初の90秒を実時間で（筆の掴み取り・ディップ・最初のストローク）
$ .venv/bin/painter gcode-sim out/fuji04/program.gcode -o out/fuji04/gcode_start --video --start 0 --end 90 --speed 1
```
`gcode-sim` のチェック内容: 可動範囲・回転軸 A の上限、キャンバスと各ステーション以外への接触、筆なし/絵の具なしでの描画、
汚れた筆で別の色を取る（混色汚染）、押し込みすぎ、汚れた筆のラック戻し。エラーがあれば終了コード 1。

### カメラで見ながら描く（クローズドループ）
```bash
# 層ごとにキャンバスを撮影 → 補正 → 目標とのズレを見て次の層を計画。最後に細筆でタッチアップ
$ .venv/bin/painter loop date/raw_images/gemini_fuji_04.jpeg -o out/fuji04/loop --video
#   comparison.png    目標 / 見ずに描いた場合（オープンループ）/ カメラで見ながら描いた場合
#   camera_steps.png  各層の撮影画像（補正後）と目標とのズレのヒートマップ
#   camera_loop.mp4   カメラ視点の描画過程 + 直前の撮影で見えたズレ
#   steps/            各層の生の撮影画像・補正画像・ズレ画像
#   loop_report.json  層ごとの ΔE / SSIM / ズレ面積、ストローク数、推定時間
```
シミュレーションでは「実機は計画のモデル通りに描けない」状況を意図的に作っています（筆が開いて線が太い、絵の具の乗りが薄い、
位置ズレ、人が混ぜた色のズレ）。`--width-scale --opacity --position-noise --mix-error` で変えられます。
カメラの位置は `configs/machine.yaml` の `camera.canvas_corners`（撮影画像中のキャンバス四隅）で指定します。

| 設定 | 場所 |
| --- | --- |
| キャンバス・パレット・油壺・布・筆ラックの位置、筆の種類 | `configs/machine.yaml` |
| 細部の描き込み量（多いほど時間増） | `--threshold`, `--threshold-growth` |
| パレット色数 | `--colors`（パレットのスロット数以下） |

## デジタルツイン（最終実機の 3D 再生、`painter twin`）
`docs/rig_plan.md` §2 の平台プロッタ型（作業範囲 700×450、`configs/machine_final.yaml`）が 1 枚を描く工程を、ブラウザの 3D ビューアで再生する。
画像 → 工程計画 → G-code → G-code シミュレータ（Klipper マクロ込み、ステーション位置は config から自動で差し替え）の動きをそのまま使うので、
ガントリー・Z のばね・回転 A・筆替え・洗浄・絵の具の取り方と、キャンバスに描かれていく様子が同じ時間軸で見られる。

```bash
$ .venv/bin/painter -c configs/machine_final.yaml twin date/raw_images/gemini_fuji_04.jpeg -o out/twin_fuji04
$ python -m http.server -d out/twin_fuji04 8000     # http://127.0.0.1:8000（file:// では開けない）
```
- 出力は `index.html` と `twin_data.json`（富士山 1 枚 = 約 40 万移動・3 万ストロークで 7.7MB）
- 視点: 全体 / 真上 / ヘッド追従 / ステーション。速度は実時間〜6000 倍、タイムラインの目盛りは筆替え（青）と補充の一時停止（茶）
- 寸法は設計目標値。洗浄は壺 1 つで再現している（§2 の 2 つ目の壺は未対応）

## 完成機の CAD（`machine/`）
平台プロッタ型の完成機を Python（manifold3d）で作ったもの。配置は `configs/machine_final.yaml` から読み、ソフト・デジタルツインと同じ値になる。

```bash
$ uv pip install --python .venv/bin/python -e '.[cad]'
$ .venv/bin/python machine/cad/machine.py           # STL・組立 GLB・部品表・天板の切り出し図・プレビュー
$ python -m http.server -d machine/cad 8000         # http://127.0.0.1:8000/viewer.html
```
詳細・チェック内容・部品表は `machine/README.md`。試験装置（筆 1 本）の部品は `rig/README.md`。

## スタイル変換 Web UI（`painter webui`）
画像をアップロードすると、ローカル GPU 上の生成AIで油絵・ゴッホ風・モネ風・浮世絵・水彩・点描・フォーヴィスム（または自由なプロンプト）に変換する。
結果を選んで「油絵シミュレーション」を押すと、上の painter パイプラインにそのまま流し、キャンバス・パレット・工程動画・G-code を表示する。

- モデル：SDXL img2img ＋ ControlNet(Canny)。輪郭（構図）を保ったまま画風だけを変える。初回起動時に Hugging Face から約 10GB を取得する
- 必要なもの：VRAM 12GB 以上の空き（RTX 5090 で 1 枚約 3.5 秒、ピーク 11.4GiB）。空きが足りないときは自動で CPU offload に切り替わる
- 入力は jpg / png / webp / HEIC(iPhone) など。HEIC は EXIF の向きを反映して読み込む（`painter run photo.heic` も可）
- 出力は `out/webui/<日時>/`（input.png, styled_N.png, style.json, sim_N/）

```bash
$ uv pip install -e '.[dev,style]' --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
#   社内プロキシ環境では SSL_CERT_FILE=<CA bundle> を設定し、uv に --native-tls を付ける
$ .venv/bin/painter webui                  # http://127.0.0.1:7860
$ .venv/bin/painter webui --host 0.0.0.0   # 他の PC からも開く
$ .venv/bin/painter webui --offload        # 常に CPU offload（GPU を他の処理と共用するとき）
```

### GPU が弱い PC では Gemini（クラウド）で変換する
VRAM 12GB 未満や GPU なしの PC では、`--backend auto`（既定）が自動で Gemini API を使う。torch は不要（インストール約 500MB）。
アップロードした画像は Google に送信され、生成ごとに API の料金がかかる。Gemini では strength / ControlNet / steps は使わず（画面からも隠れる）、「構図はそのまま、画風だけ変える」ように指示している。

```bash
$ uv venv && uv pip install -e '.[gemini]'
$ export GEMINI_API_KEY=<Google AI Studio で発行したキー>
$ .venv/bin/painter webui                          # auto: GPU が弱ければ Gemini
$ .venv/bin/painter webui --backend gemini         # GPU があっても Gemini を使う
$ .venv/bin/painter webui --gemini-model <モデル名>  # 既定 gemini-2.5-flash-image
```

| 設定 | 意味 |
| --- | --- |
| strength | 元画像からどれだけ離れるか。0.8 以下だと写真のまま残りやすい（既定 0.95） |
| ControlNet scale | 輪郭の保持の強さ。上げると構図に忠実、下げると画風が強く出る（既定 0.45） |
| 枚数 / seed | seed を 1 ずつ変えて複数枚生成。ギャラリーで選んだ 1 枚をシミュレーションする |
