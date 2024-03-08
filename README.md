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
```python
$ git clone git@github.com:Bucchiman/Ro8arm_picture.git
$ cd Ro8arm_picture
$ python -m venv venv
$ pip install opencv-python adafruit_pca9685
$ sudo chmod 777 /dev/i2c-1
$ python ./src/fuji.py
```
