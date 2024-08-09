import os
import hashlib
import time
import random
import string
import requests
import urllib
import xml.etree.ElementTree as ET
from collections import Counter
from openpyxl import Workbook
from django.shortcuts import render, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from core.models import Paper, Payment
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from base64 import b64encode, b64decode
import qrcode
from io import BytesIO
from django.http import JsonResponse, HttpResponseBadRequest
import base64
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from mysite import settings

def generate_order_id():
    timestamp = int(time.time())
    num_1 = int(timestamp / 100000)
    num_2 = timestamp % 100000
    num_3 = random.randint(1, 9999)
    return f"{num_1:05}-{num_2:05}-{num_3:04}"

def generate_sign(params, api_key):
    # 生成签名字符串
    stringA = '&'.join([f'{k}={params[k]}' for k in sorted(params)])
    stringSignTemp = f"{stringA}&key={api_key}"

    # 使用 MD5 生成签名
    sign = hashlib.md5(stringSignTemp.encode('utf-8')).hexdigest().upper()
    return sign

def generate_nonce_str(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_paginated_reviews(reviews, page_number):
    if page_number is None:
        page_number = 1

    p = Paginator(reviews, 20)
    try:
        reviews = p.get_page(page_number)
    except PageNotAnInteger:
        page_number = 1
        reviews = p.page(1)
    except EmptyPage:
        page_number = p.num_pages
        reviews = p.page(p.num_pages)

    items = list(reviews)
    indices = list(range((reviews.number - 1) * p.per_page + 1, reviews.number * p.per_page + 1))

    return reviews, zip(items, indices)

def home(request):
    papers = Paper.objects.all()

    query = request.GET.get('q') or ''
    if query:
        papers = Paper.objects.filter(
            Q(title__icontains=query) |
            Q(journal__icontains=query) |
            Q(doi = query) |
            Q(pmid = query) |
            Q(article_type__icontains=query) |
            Q(description__icontains=query) |
            Q(novelty__icontains=query) |
            Q(limitation__icontains=query) |
            Q(research_goal__icontains=query) |
            Q(research_objects__icontains=query) |
            Q(field_category__icontains=query) |
            Q(disease_category__icontains=query) |
            Q(technique__icontains=query) |
            Q(model_type__icontains=query) |
            Q(data_type__icontains=query) |
            Q(sample_size__icontains=query))

    pub_year = request.GET.get('pub_year') or ''
    pub_month = request.GET.get('pub_month') or ''
    if pub_year:
        papers = papers.filter(pub_date_dt__year=pub_year)
        if pub_month:
            papers = papers.filter(pub_date_dt__month=pub_month)

    papers = papers.order_by('-source', '-pub_date_dt')

    page_number = request.GET.get('page')
    papers, items = get_paginated_reviews(papers, page_number)

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']

    for index, paper in enumerate(papers):
        paper.index = index + papers.start_index()
        if paper.parse_time is None:
            paper.parse_time = paper.created
        if paper.article_type is None or paper.article_type == '':
            paper.article_type = 'NA'
        if paper.description is None or paper.description == '':
            paper.description = 'NA'
        if paper.novelty is None or paper.novelty == '':
            paper.novelty = 'NA'
        if paper.limitation is None or paper.limitation == '':
            paper.limitation = 'NA'
        if paper.research_goal is None or paper.research_goal == '':
            paper.research_goal = 'NA'
        if paper.research_objects is None or paper.research_objects == '':
            paper.research_objects = 'NA'
        if paper.field_category is None or paper.field_category == '':
            paper.field_category = 'NA'
        if paper.disease_category is None or paper.disease_category == '':
            paper.disease_category = 'NA'
        if paper.technique is None or paper.technique == '':
            paper.technique = 'NA'
        if paper.model_type is None or paper.model_type == '':
            paper.model_type = 'NA'
        if paper.data_type is None or paper.data_type == '':
            paper.data_type = 'NA'
        if paper.sample_size is None or paper.sample_size == '':
            paper.sample_size = 'NA'

    return render(request, 'core/home.html', {
        'query': query,
        'pub_year': pub_year,
        'pub_month': pub_month,
        'get_params': get_params,
        'papers': papers,
        'items': items,
    })

def stat(request):
    papers = Paper.objects.all().order_by('-pub_date_dt')
    year_counts = Counter([paper.pub_date_dt.year for paper in papers])
    month_counts = Counter([f"{paper.pub_date_dt.year}-{paper.pub_date_dt.month:02}" for paper in papers])

    years = sorted(year_counts.keys(), reverse=True)  # 获取所有年份并按倒序排列
    months = [f"{i:02d}" for i in range(1, 13)]  # 生成月份列表

    # 构造一个包含所有数据的二级列表
    data = []
    for year in years:
        year_data = {'year': year, 'total': year_counts[year], 'months': []}
        for month in months:
            count = month_counts.get(f"{year}-{month}", 0)
            year_data['months'].append({'month': month, 'count': count})
        data.append(year_data)

    context = {
        'data': data,
        'months': months,
    }
    return render(request, 'core/stat.html', context)

def all_papers_to_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Papers"
    ws.append([
        "标题", "杂志", "发表日期", "DOI", "PMID",
        "类型", "简述", "创新点", "不足", "研究目的", "研究对象",
        "领域", "病种", "技术", "模型", "数据类型", "样本量"
    ])
    for papers in Paper.objects.all():
        ws.append([
            papers.title,
            papers.journal,
            papers.pub_date,
            papers.doi,
            papers.pmid,
            papers.article_type,
            papers.description,
            papers.novelty,
            papers.limitation,
            papers.research_goal,
            papers.research_objects,
            papers.field_category,
            papers.disease_category,
            papers.technique,
            papers.model_type,
            papers.data_type,
            papers.sample_size
            ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="papers.xlsx"'
    wb.save(response)
    return response

import time
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

def get_cert_serial_no(cert_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography import x509

    with open(cert_path, 'rb') as cert_file:
        cert_data = cert_file.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    serial_number = cert.serial_number
    cert_data = format(serial_number, 'x').upper()
    print(f"Cert serial number: {cert_data}")
    return cert_data
    # 从证书中读取序列号
    with open(cert_path, 'rb') as cert_file:
        cert_data = cert_file.read()
    # 使用相关库提取序列号（这个过程可能需要依赖特定的库）
    return cert_data # 'your_cert_serial_no_here'  # 例如 '444D6A1EFFFFFFFF'

def generate_v3_headers(payload):
    apiclient_cert_file = os.path.join(settings.BASE_DIR, os.getenv('WEB_CERT_PATH'))
    apiclient_key_file = os.path.join(settings.BASE_DIR, os.getenv('WEB_KEY_PATH'))

    mchid = os.getenv('WEB_MERCHANT_ID')
    serial_no = get_cert_serial_no(apiclient_cert_file)
    timestamp = str(int(time.time()))
    nonce_str = generate_nonce_str()

    # 生成签名的字符串
    sign_str = f"POST\n/v3/pay/transactions/native\n{timestamp}\n{nonce_str}\n{payload}\n"

    # 加载私钥
    with open(apiclient_key_file, 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )

    # 签名
    signature = private_key.sign(
        sign_str.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature = base64.b64encode(signature).decode('utf-8')

    headers = {
        "Authorization": f'WECHATPAY2-SHA256-RSA2048 mchid="{mchid}",serial_no="{serial_no}",nonce_str="{nonce_str}",timestamp="{timestamp}",signature="{signature}"',
        "Content-Type": "application/json"
    }

    return headers

def wx_create_payment_order():
    apiclient_cert_file = os.path.join(settings.BASE_DIR, os.getenv('WEB_CERT_PATH'))
    apiclient_key_file = os.path.join(settings.BASE_DIR, os.getenv('WEB_KEY_PATH'))

    url = "https://api.mch.weixin.qq.com/v3/pay/transactions/native"
    payload = {
        "mchid": os.getenv('WEB_MERCHANT_ID'),
        "appid": os.getenv('WEB_APP_ID'),
        "description": '购买单细胞与空转测序相关文章可下载表格（Excel文件）',
        "out_trade_no": generate_order_id(),
        "notify_url": f"https://{os.getenv('WEB_DOMAIN')}/wx_payment_callback/",  # 微信支付成功后通知的URL
        "amount": {
            "total": 1000, # 订单金额，单位为分
            "currency": "CNY"
        }
    }

    # 转换为JSON
    json_payload = json.dumps(payload)

    # 获取签名（使用你自己的签名函数）
    headers = generate_v3_headers(json_payload)

    # 发送请求
    response = requests.post(
        url,
        headers=headers,
        data=json_payload,
        cert=(
            apiclient_cert_file,
            apiclient_key_file
        )
    )
    if response.status_code != 200:
        raise Exception(f"Failed to create order: {response.content}")

    # 解析响应
    response_data = response.json()
    qr_code_url = response_data.get("code_url")
    print(f"QR code URL: {qr_code_url}")
    return qr_code_url

def wx_create_payment(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method")
    print(request.body)

    # 模拟订单生成
    out_trade_no = f"ORDER_{int(time.time())}"
    total_fee = 1000  # 订单金额（单位为分）
    description = "Test product"

    # 发起微信支付请求并获取支付二维码的URL
    qr_url = wx_create_payment_order()

    # 生成二维码
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # 将二维码图像转换为Base64编码
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 返回二维码图像的Base64字符串
    return JsonResponse({
        "qr_image": img_str,
        "out_trade_no": out_trade_no
    })

@csrf_exempt
def wx_payment_callback(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method")

    data = json.loads(request.body)
    event_type = data.get('event_type')

    # 检查订单状态
    if event_type == "TRANSACTION.SUCCESS":
        transaction_id = data["resource"]["ciphertext"]["transaction_id"]
        out_trade_no = data["resource"]["ciphertext"]["out_trade_no"]

        # 验证订单并更新状态（示例）
        try:
            payment = Payment.objects.get(out_trade_no=out_trade_no)
            payment.status = "SUCCESS"
            payment.transaction_id = transaction_id
            payment.save()
        except Payment.DoesNotExist:
            return HttpResponse("Order not found", status=404)

        return HttpResponse("Success", status=200)
    else:
        return HttpResponse("Invalid event type", status=400)

def generate_state():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def wx_get_qr_code(request):
    state = generate_state()
    request.session['wx_state'] = state

    weixin_auth_url = "https://open.weixin.qq.com/connect/qrconnect"
    params = {
        "appid": os.getenv('WEB_APP_ID'),
        "redirect_uri": f'https://{os.getenv("WEB_DOMAIN")}/wx_login_callback/',
        "response_type": "code",
        "scope": "snsapi_login",
        "state": state
    }
    auth_url = f"{weixin_auth_url}?{urllib.parse.urlencode(params)}#wechat_redirect"
    return JsonResponse({'url': auth_url})

def get_openid(code):
    APP_ID = os.getenv('WEB_APP_ID')
    SECRET = os.getenv('WEB_APP_SECRET')
    if not APP_ID or not SECRET:
        print(f"Invalid APP_ID or SECRET: '{APP_ID}', '{SECRET}'")
        return None

    url = "https://api.weixin.qq.com/sns/oauth2/access_token"
    params = {
        "appid": APP_ID,
        "secret": SECRET,
        "code": code,
        "grant_type": "authorization_code"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Failed to get session_key: {response.text}")
        return None
    json_data = response.json()
    if json_data.get('errcode', 0) != 0:
        print(f"Failed to get session_key: {response.text}")
        return None

    openid = json_data.get('openid')
    return openid

def wx_login_callback(request):
    received_state = request.GET.get('state')
    code = request.GET.get('code')

    # 从会话中获取原始 state
    original_state = request.session.get('wx_state')

    # 验证 state
    if not original_state or received_state != original_state:
        return HttpResponseBadRequest("Invalid state parameter")

    # state 验证通过，可以继续处理 code 并向微信请求 access_token
    # 您可以在此处向微信服务器发出请求，使用 code 获取 access_token 和 openid
    openid = get_openid(code)
    if not openid:
        return HttpResponseBadRequest("Login failed")

    if request.user.is_authenticated:
        user = request.user
    else:
        # 如果用户未登录，尝试查找或创建用户
        user, created = User.objects.get_or_create(username=openid)
        if created:
            # 可以在这里设置默认密码，或者使用随机密码
            user.set_unusable_password()
            user.save()

    payment_list = Payment.objects.filter(openid=openid)
    if payment_list.count() == 0:
        payment = Payment(user=user, openid=openid)
        payment.order_number = generate_order_id()
        payment.save()
    else:
        payment = payment_list[0]
        if payment.order_number is None:
            payment.order_number = generate_order_id()
            payment.save()

    login(request, user)

    # 清理 session 中的 state 以防止重用
    del request.session['wx_state']

    return redirect('download')

def download(request):
    user = request.user
    if not user.is_authenticated:
        return render(request, 'core/login.html')

    payment = Payment.objects.get(user=user)
    if not payment.has_paid:
        if payment.order_number is None:
            payment.order_number = generate_order_id()
            payment.save()
        return render(request, 'core/payment.html', {
            'order_number': payment.order_number
        })

    if request.method == 'POST':
        if request.POST.get('csrfmiddlewaretoken'):
            if payment.has_paid:
                return all_papers_to_excel()

    return render(request, 'core/download.html')

def do_logout(request):
    logout(request)
    return redirect('home')
