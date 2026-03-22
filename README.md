# Zalo Auto Reply Bot (Python + Web Admin + GitHub + Render)

Bot Zalo trả lời tin nhắn tự động bằng **Python/Flask**, có **web admin** để quản lý rule phản hồi, lưu **log tin nhắn**, và sẵn file **`render.yaml`** để deploy lên **Render** từ **GitHub**.

## 1) Chức năng có sẵn

| Nhóm chức năng | Mô tả |
|---|---|
| Webhook Zalo OA | Nhận sự kiện tin nhắn từ Zalo Official Account |
| Auto reply | Tìm rule theo thứ tự ưu tiên và gửi phản hồi tự động |
| Web admin | Đăng nhập admin, thêm/sửa/xóa rule |
| Log | Lưu nội dung tin nhắn vào, rule khớp, kết quả gửi phản hồi |
| Test send | Gửi thử một tin nhắn từ trang admin bằng `user_id` |
| Deploy | Chạy local, push GitHub, deploy Render |

---

## 2) Kiến trúc hoạt động

```text
Người dùng Zalo
      |
      v
Zalo Official Account
      |
      v
Webhook: /webhook/zalo
      |
      v
Flask App
  |- extract message
  |- find matching rule
  |- call Zalo API send message
  |- save logs
      |
      v
Admin Web (/admin)
  |- CRUD rule
  |- xem log
  |- test gửi tin
```

---

## 3) Điều kiện để bot chạy đúng

Bot này được thiết kế cho **Zalo Official Account (OA)**.

Bạn cần chuẩn bị:

1. Một **Zalo OA**
2. Một **ứng dụng trên Zalo Developers** liên kết với OA
3. Lấy các thông tin sau:
   - `ZALO_ACCESS_TOKEN`
   - `ZALO_APP_ID`
   - `ZALO_OA_SECRET_KEY`
4. Cấu hình webhook của OA trỏ đến:

```bash
https://ten-app-cua-ban.onrender.com/webhook/zalo
```

---

## 4) Cấu trúc thư mục

```bash
zalo_autoreply_bot/
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ extensions.py
│  ├─ models.py
│  ├─ services.py
│  ├─ zalo.py
│  └─ templates/
│     ├─ base.html
│     ├─ index.html
│     └─ admin/
│        ├─ dashboard.html
│        ├─ login.html
│        ├─ logs.html
│        ├─ rule_form.html
│        └─ setup.html
├─ .env.example
├─ app.py
├─ requirements.txt
├─ render.yaml
└─ README.md
```

---

## 5) Cài đặt local

### 5.1 Tạo môi trường ảo

```bash
python -m venv venv
```

### 5.2 Kích hoạt môi trường

**Windows**

```bash
venv\Scripts\activate
```

**macOS / Linux**

```bash
source venv/bin/activate
```

### 5.3 Cài thư viện

```bash
pip install -r requirements.txt
```

### 5.4 Tạo file `.env`

Copy từ file mẫu:

```bash
cp .env.example .env
```

Điền giá trị thật:

```env
SECRET_KEY=replace-with-a-random-secret
DATABASE_URL=sqlite:///zalo_bot.db
ZALO_ACCESS_TOKEN=your-zalo-oa-access-token
ZALO_APP_ID=your-zalo-app-id
ZALO_OA_SECRET_KEY=your-zalo-oa-secret-key
ZALO_VALIDATE_SIGNATURE=false
ZALO_API_BASE=https://openapi.zalo.me
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ChangeThisPassword123
```

> Giai đoạn test local có thể để `ZALO_VALIDATE_SIGNATURE=false` để kiểm tra luồng. Khi đưa production, nên bật `true` sau khi xác minh chắc header webhook từ Zalo đang đúng với công thức ký của OA.

### 5.5 Chạy ứng dụng

```bash
flask --app app.py run
```

Hoặc:

```bash
python app.py
```

Ứng dụng chạy ở:

```bash
http://127.0.0.1:5000
```

---

## 6) Đăng nhập admin

Trang đăng nhập:

```bash
http://127.0.0.1:5000/admin/login
```

Nếu database chưa có admin, app sẽ tự tạo user mặc định theo biến môi trường:

| Biến | Giá trị mẫu |
|---|---|
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | `ChangeThisPassword123` |

---

## 7) Cách tạo rule auto reply

Trong admin, mỗi rule có các trường:

| Trường | Ý nghĩa |
|---|---|
| Tên rule | Tên để quản trị |
| Kiểu khớp | `contains`, `exact`, `starts_with`, `fallback` |
| Từ khóa | Nội dung cần dò trong tin nhắn người dùng |
| Nội dung trả lời | Tin bot sẽ gửi lại |
| Ưu tiên | Số nhỏ hơn sẽ được kiểm tra trước |
| Trạng thái | Bật / tắt rule |

### Ví dụ rule

| Ưu tiên | Kiểu khớp | Từ khóa | Tin nhắn trả lời |
|---:|---|---|---|
| 1 | exact | giá | Bên mình sẽ gửi bảng giá ngay cho bạn. |
| 2 | contains | địa chỉ | Cửa hàng ở số 123 Nguyễn Huệ, Quận 1. |
| 3 | starts_with | khuyến mãi | Chương trình khuyến mãi hôm nay giảm 15%. |
| 999 | fallback | *(trống)* | Cảm ơn bạn đã nhắn tin. Admin sẽ phản hồi sớm. |

---

## 8) Test webhook local bằng công cụ gửi POST

Ví dụ payload test:

```bash
curl -X POST http://127.0.0.1:5000/webhook/zalo \
  -H "Content-Type: application/json" \
  -d '{
    "sender": {"id": "2512523625412515"},
    "message": {"text": "giá"},
    "event_name": "user_send_text"
  }'
```

Nếu rule khớp, app sẽ:

1. Lưu log vào database
2. Gọi API gửi tin của Zalo
3. Trả về JSON kết quả xử lý

---

## 9) Deploy lên GitHub

### 9.1 Tạo repository mới

Ví dụ:

```bash
git init
git add .
git commit -m "Initial commit: Zalo auto reply bot"
```

### 9.2 Kết nối GitHub

```bash
git branch -M main
git remote add origin https://github.com/USERNAME/REPO_NAME.git
git push -u origin main
```

---

## 10) Deploy lên Render

Project đã có sẵn file `render.yaml`.

### Cách triển khai

1. Push code lên GitHub
2. Vào Render
3. Kết nối GitHub repo
4. Chọn deploy bằng `render.yaml`
5. Điền các biến môi trường còn thiếu:
   - `ZALO_ACCESS_TOKEN`
   - `ZALO_APP_ID`
   - `ZALO_OA_SECRET_KEY`
   - `ADMIN_PASSWORD`
6. Sau khi deploy xong, lấy URL public dạng:

```bash
https://zalo-auto-reply-bot.onrender.com
```

7. Gắn vào webhook Zalo:

```bash
https://zalo-auto-reply-bot.onrender.com/webhook/zalo
```

---

## 11) Giải thích file `render.yaml`

| Thành phần | Ý nghĩa |
|---|---|
| `databases` | Tạo PostgreSQL trên Render |
| `services.type = web` | Tạo web service Flask |
| `buildCommand` | Cài thư viện Python |
| `startCommand` | Chạy app bằng Gunicorn |
| `healthCheckPath` | Route kiểm tra sống `/healthz` |
| `envVars` | Khai báo biến môi trường và nối DB |

---

## 12) Các route quan trọng

| Route | Method | Mục đích |
|---|---|---|
| `/` | GET | Trang giới thiệu |
| `/healthz` | GET | Kiểm tra app còn sống |
| `/webhook/zalo` | GET/POST | Endpoint webhook của Zalo |
| `/admin/login` | GET/POST | Đăng nhập admin |
| `/admin` | GET | Dashboard |
| `/admin/rules/new` | GET/POST | Tạo rule |
| `/admin/rules/<id>/edit` | GET/POST | Sửa rule |
| `/admin/rules/<id>/delete` | POST | Xóa rule |
| `/admin/logs` | GET | Xem log |
| `/admin/test-send` | POST | Gửi tin test thủ công |

---

## 13) Lưu ý production

### 13.1 SQLite không phù hợp lâu dài trên Render

Ở local bạn có thể dùng SQLite:

```env
DATABASE_URL=sqlite:///zalo_bot.db
```

Trên Render nên dùng PostgreSQL để tránh mất dữ liệu sau redeploy hoặc restart.

### 13.2 Về xác thực chữ ký webhook

Code hiện đã có hàm `validate_webhook_signature()`.

- Nếu `ZALO_VALIDATE_SIGNATURE=false`: app bỏ qua kiểm tra chữ ký
- Nếu `ZALO_VALIDATE_SIGNATURE=true`: app sẽ kiểm tra header webhook theo cấu hình `ZALO_APP_ID` và `ZALO_OA_SECRET_KEY`

### 13.3 Cần kiểm tra lại payload thực tế từ OA

Zalo có thể gửi payload khác nhau tùy loại sự kiện. Trong file `app/zalo.py`, hàm `extract_message_data()` đang viết theo kiểu mềm dẻo để cố gắng bóc `user_id` và `text` từ nhiều cấu trúc JSON khác nhau.

Nếu webhook thực tế của OA bạn có format khác, chỉ cần sửa nhẹ hàm này.

---

## 14) Mở rộng tiếp theo bạn có thể làm

| Hạng mục | Mục tiêu |
|---|---|
| Upload file / ảnh | Gửi media reply thay vì text thuần |
| Rule theo regex | Khớp nâng cao |
| Multi-OA | Quản lý nhiều tài khoản OA trong cùng web admin |
| Phân quyền admin | Nhiều user quản trị |
| AI fallback | Khi không khớp rule thì gọi OpenAI / LLM |
| Thống kê | Biểu đồ số tin theo ngày, rule nào được dùng nhiều nhất |
| Export log | Xuất CSV / Excel |

---

## 15) Tài khoản nào phù hợp?

| Loại tài khoản | Có phù hợp không | Ghi chú |
|---|---|---|
| Zalo cá nhân | Không phù hợp | Không phải luồng chuẩn để tích hợp chatbot server-side |
| Zalo Official Account (OA) | Phù hợp | Đây là hướng chính thức để nhận webhook và gửi tin qua API |

---

## 16) Checklist triển khai nhanh

- [ ] Tạo OA
- [ ] Tạo app trên Zalo Developers
- [ ] Lấy Access Token
- [ ] Lấy App ID
- [ ] Lấy OA Secret Key
- [ ] Push code lên GitHub
- [ ] Deploy repo lên Render
- [ ] Cấu hình webhook OA trỏ tới `/webhook/zalo`
- [ ] Đăng nhập `/admin/login`
- [ ] Tạo rule đầu tiên
- [ ] Test nhắn tin thật từ Zalo

---

## 17) Lệnh chạy production mẫu

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

---

## 18) Gợi ý bước tiếp theo

Sau khi chạy thành công bản này, bước nâng cấp hợp lý nhất là:

1. thêm **quản lý nhiều OA**,
2. thêm **thống kê dashboard**,
3. thêm **AI fallback** khi không có rule nào khớp.
