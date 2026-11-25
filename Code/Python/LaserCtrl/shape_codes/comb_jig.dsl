# Comb jig — khung đỡ que kem (một tấm phẳng, viền ngoài kín)
# Đơn vị: mm. Gốc toạ độ (0, 0) ở góc trái dưới của đế.
#
# Đế (base): hình chữ nhật 140 × 30, nằm dưới để liên kết các răng.
# 10 răng: mỗi răng rộng 5, cao 50; răng đầu bắt đầu tại x=0,
#   răng cuối kết thúc tại x=140.
# 9 khe: mỗi khe rộng 10 (bằng bề rộng que kem). Không cộng dung sai
#   vì kerf laser sẽ ôm sát que.
# Tổng chiều cao: 30 + 50 = 80.
#
# P là đa giác (polygon) tự động nối đỉnh cuối về đỉnh đầu.
# Chỉ có một viền ngoài — không có đường cắt bên trong giữa đế và răng.
#
# Đỉnh đi ngược chiều kim đồng hồ, bắt đầu ở góc trái dưới:
#   đáy đế:      (0,0) -> (140,0)
#   cạnh phải:   (140,0) -> (140,80)    [đế + răng cuối thẳng hàng]
#   lược 9 khe:  mỗi răng (x_phải,80)->(x_trái,80)->(x_trái,30)
#                rồi ngang qua khe tới (x_khe_trái,30)
#   cạnh trái:   (0,80) -> (0,0)        [P tự động đóng]
# 40 đỉnh phân biệt; P thêm cạnh đóng về (0,0) (tương đương 41 đỉnh).

ADD 0 0 comb_jig
P 0 0  140 0  140 80  135 80  135 30  125 30  125 80  120 80  120 30  110 30  110 80  105 80  105 30  95 30  95 80  90 80  90 30  80 30  80 80  75 80  75 30  65 30  65 80  60 80  60 30  50 30  50 80  45 80  45 30  35 30  35 80  30 80  30 30  20 30  20 80  15 80  15 30  5 30  5 80  0 80
END
