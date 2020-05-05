from django.shortcuts import render, redirect
from apps.user.models import User, Address
from django.views.generic import View
from django.http import HttpResponse
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from utils.mixin import LoginRequiresMixin
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
import re


# Create your views here.
def register(request):
    if request.method == 'GET':
        return render(request, "register.html")
    else:
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确 '})

        # 校验是否勾选协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        try:
            # 检验用户名是否重复
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户不存在
            user = None

        if user:
            # 用户已存在
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 进行业务处理:创建用户
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        return redirect(reverse('goods:index'))


def register_handle(request):
    # 接收数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')

    # 进行数据校验
    if not all([username, password, email]):
        return render(request, 'register.html', {'errmsg': '数据不完整'})

    # 校验邮箱
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
        return render(request, 'register.html', {'errmsg': '邮箱格式不正确 '})

    # 校验是否勾选协议
    if allow != 'on':
        return render(request, 'register.html', {'errmsg': '请同意协议'})

    try:
        # 检验用户名是否重复
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # 用户不存在
        user = None

    if user:
        # 用户已存在
        return render(request, 'register.html', {'errmsg': '用户已存在'})

    # 进行业务处理:创建用户
    user = User.objects.create_user(username, email, password)
    user.is_active = 0
    user.save()
    return redirect(reverse('goods:index'))


class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确 '})
        # 校验是否勾选协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        try:
            # 检验用户名是否重复
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户不存在
            user = None
        if user:
            # 用户已存在
            return render(request, 'register.html', {'errmsg': '用户已存在'})
        # try:
        #     # 检验用户名是否重复
        #     email = User.objects.get(email=email)
        # except User.DoesNotExist:
        #     # 邮箱不存在
        #     email = None
        # if email:
        #     # 邮箱已存在
        #     return render(request, 'register.html', {'errmsg': '邮箱已存在'})
        # 进行业务处理:创建用户
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        # 加密用户身份信息
        serializer = Serializer(settings.SECRET_KEY, 1800)
        info = {'confirm': user.id}
        token = serializer.dumps(info)

        # 发邮件
        subject = '天天生鲜激活信息'
        message = ''
        sender = settings.EMAIL_FROM
        receiver = [email]
        send_mail(subject, message, sender, receiver)
        return redirect(reverse('goods:index'))


class ActiveView(View):
    ''' 用户激活 '''

    def get(self, request, token):
        print(token)
        serializer = Serializer(settings.SECRET_KEY, 1800)
        try:
            info = serializer.loads(token)
            # 获取激活用户的id
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired:
            return HttpResponse('激活连接已过期')


class LoginView(View):
    ''' 显示登录页面 '''

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})
        # 业务处理:登陆校验
        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 记录用户状态
                login(request, user)
                # 获取登录后要跳转的地址
                # 默认跳转到首页
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)  # HttpResponseRedirect

                # 判断是否需要记住用户名
                remember = request.POST.get('remember')
                print(remember)

                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')

                # 返回response
                return response
            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg': '账户未激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class LogoutView(View):
    def get(self, request):
        # 退出登录,清除用户的session信息
        logout(request)
        return redirect(reverse('goods:index'))


class UserInfoView(LoginRequiresMixin, View):
    def get(self, request):
        user = request.user
        address = Address.objects.get_default_address(user)
        con = get_redis_connection('default')
        history_key = 'history_%s' % user.id
        sku_ids = con.lrange(history_key, 0, 4)
        goods_li = list()
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        context = {
            'page': 'user',
            'address': address,
            'goods_li': goods_li
        }
        return render(request, 'user_center_info.html', context)


class UserOrderView(LoginRequiresMixin, View):
    def get(self, request):
        return render(request, 'user_center_order.html', {'page': 'order'})


class AddressView(LoginRequiresMixin, View):
    def get(self, request):
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})
        if not re.match('^1[3|4|5|7|8|9][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机号不正确'})
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        return redirect(reverse('user:address'))
