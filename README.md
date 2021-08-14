# serial_flash_writer
Serial flash memory writer using pyboard.

Japanese only

## 概要

pyboard から Serial flash memory への書き込みを行う python script です。

## 対応メモリ

|Vendor|Name|Capacity|
|--|--|--|
|Microchip|25AA640A|64KBit|
|Microchip|25LC640A|64KBit|
|Microchip|ST25VF032B|32MBit|
|Macronix|MX25L4006E|4MBit|
|Winbond|W25Q32JV-IQ|32MBit|

上記以外にも、データシートから使用できると思われるもの(単なる容量違い等)がありますが、実物での動作を確認できていないため除外しています(コメントとして記述はしています)。

## pyboard との接続方法

serial_flash_writer.py で想定している結線は以下の通りです(8pin SPI Flash の場合)。

![connection](https://user-images.githubusercontent.com/14823909/129433088-7f769f18-8f42-4aed-8b8e-8a096e8da241.png)

## 使い方

* ファイルの内容をメモリへ書き込む script として serial_flash_writer.py を実装しています。
* serial_flash_writer を import して、from_file(<ファイル名>) で書き込みを行います。
* 以下は REPL 上での実行、出力例です。
```
>>> import serial_flash_writer
>>> serial_flash_writer.from_file('player.img')
JEDEC ID : 0xC2 0x20 0x13
Vendor   : Macronix
Name     : MX25x40xx
Capacity : 524288 bytes
Erasing...
Writing: 000000-0003ff
Writing: 000400-0007ff
Writing: 000800-000bff
Writing: 000c00-000fff
Writing: 001000-0013ff
Writing: 001400-0017ff
Writing: 001800-001bff
Writing: 001c00-001fff
Writing: 002000-0023ff
Writing: 002400-0027ff
Writing: 002800-002980
Completed.
```

25AA640A 等、JEDEC ID が読み出せないメモリは以下の様に from_file へ引数を追加します。
```
serial_flash_writer.from_file('player.img', '25AA640A')
```

## 実装について

* serial_flash_accessor/ 以下に Flash メモリへのアクセスライブラリを package 化しています。
  * メモリによって書き込み方法が異なるため、ファミリー(MX25xxxx, W25xxxx 等)毎にクラスがあります。
* メモリは JEDEC ID を読み出して判別します。
  * JEDEC ID を読み出せないメモリ(25AA640A 等)の場合はオプションで名前を指定します。
* 全体を書き換える使い方を想定しています。
  * 可能な操作は、情報(名前、容量等)、消去、プロテクトOn/Off、読み書き(アドレス指定)程度です。
  * セキュリティ機能や、ブロック単位のプロテクト操作は実装していません。


