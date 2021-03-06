from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import ListView

from .forms import ArticlePostForm
from .models import ArticlePost
from comment.models import Comment

import markdown


# 列表通用视图
# class ArticleListView(ListView):



# 视图函数
def article_list(request):
    search = request.GET.get('search')
    order = request.GET.get('order')
    # 用户搜索逻辑
    if search:
        if order == 'total_views':
            article_list = ArticlePost.objects.filter(Q(title__icontains=search) | Q(body__icontains=search)
                                                      ).order_by('-total_views')
        else:
            article_list = ArticlePost.objects.filter(Q(title__icontains=search) | Q(body__icontains=search))
    else:
        # 将 search 参数重置为空
        search = ""
        if order =='total_views':
            article_list = ArticlePost.objects.all().order_by('-total_views')
        else:
            article_list = ArticlePost.objects.all()

    '''
    if request.GET.get('order') == 'total_views':
        article_list = ArticlePost.objects.all().order_by('-total_views')
        order = 'total_views'
    else:
        article_list = ArticlePost.objects.all()
        order = 'normal' 
    '''
    # 每页显示 1 篇文章
    paginator = Paginator(article_list, 3)
    # 获取 url 中的页码
    page = request.GET.get('page')
    # 将导航对象响应的页面内容返回给 articles
    articles = paginator.get_page(page)
    # 需要传递给模板
    context = {'articles': articles, 'order': order, 'search': search}
    # render函数：载入模板，并返回context对象
    return render(request, 'article/list.html', context)


# 文章详情
def article_detail(request, id):
    # 取出相应的文章
    article = ArticlePost.objects.get(id=id)
    # 提取文章评论
    comments = Comment.objects.filter(article=id)
    # 浏览量 +1
    article.total_views += 1
    article.save(update_fields=['total_views'])

    # 将markdown语法渲染成html样式
    md = markdown.Markdown(extensions=[
                                         # 包含 缩写、表格等常用扩展
                                         'markdown.extensions.extra',
                                         # 语法高亮扩展
                                         'markdown.extensions.codehilite',
                                         # 目录扩展
                                         'markdown.extensions.toc',
                                     ])
    article.body = md.convert(article.body)
    # 需要传递给模板的对象
    context = {'article': article, 'toc': md.toc, 'comments':comments}
    # 载入模板，并返回context对象
    return render(request, 'article/detail.html', context)


# 写文章的视图
# 检查登录
@login_required(login_url='/userprofile/login')
def article_create(request):
    # 判断用户是否提交数据
    if request.method == 'POST':
        # 将提交的数据赋值到单表实例中
        article_post_form = ArticlePostForm(data=request.POST)
        # 判断提交的数据是否满足模型的要求
        if article_post_form.is_valid():
            # 保存数据，单暂时不提交到数据库中
            new_article = article_post_form.save(commit=False)
            # 指定数据库中 id=1 的用户为作者
            # 如果你进行过删除数据表的操作，可能会找不到 id=1 的用户
            # 此时请重新创建用户，并传入此用户的id
            new_article.author = User.objects.get(id=request.user.id)
            # 将新文章保存到数据库中
            new_article.save()
            return redirect("article:article_list")
        # 如果数据不合法，返回错误信息
        else:
            return HttpResponse("表单内容有误，请重新填写。")
    # 如果用户请求获取数据
    else:
        # 创建表单类实例
        article_post_form = ArticlePostForm()
        # 赋值上下文
        context = {'article_post_form': article_post_form}
        # 返回模板
        return render(request, 'article/create.html', context)


# 删除文章（不安全）
def article_delete(request, id):
    # 根据 id 获得需要删除的文章
    article = ArticlePost.objects.get(id=id)
    # 调用delete()方法删除文章
    article.delete()
    # 完成删除后返回文章列表
    return redirect("article:article_list")


# 安全删除文章
@login_required(login_url='/userprofile/login')
def article_safe_delete(request, id):
    article = ArticlePost.objects.get(id=id)
    if request.user != article.author:
        return HttpResponse("您无权删除本文章")

    if request.method == 'POST':
        article = ArticlePost.objects.get(id=id)
        article.delete()
        return redirect("article:article_list")
    else:
        return HttpResponse("仅允许post请求")


# 更新文章
@login_required(login_url='/userprofile/login')
def article_update(request, id):
    # 获取需要修改的具体文章对象
    article = ArticlePost.objects.get(id=id)
    if request.user != article.author:          # 后端业务逻辑再次验证用户身份
        return HttpResponse("您无权编辑本文章")
    # 判断用户是否为POST提交表单数据
    if request.method == "POST":
        # 将提交的而数据赋值到表单实例中
        article_post_form = ArticlePostForm(data=request.POST)
        # 判断提交的数据是否满足模型需要
        if article_post_form.is_valid():
            # 保存新写入的 title、body 数据并保存
            article.title = request.POST['title']
            article.body = request.POST['body']
            article.save()
            # 完成后返回到修改后的文章中。需要传入文章的id值
            return redirect("article:article_detail", id=id)
        # 如果数据不合法，返回错误信息
        else:
            return HttpResponse("表单内容有误，请重新填写。")
    # 如果用户 GET 请求获取数据
    else:
        # 创建表单类实例
        article_post_form = ArticlePostForm()
        # 赋值上下文，将 article 文章对象也传递进去，以便提取旧的内容
        context = {'article': article, 'article_post_form': article_post_form}
        # 将响应返回到模板中
        return render(request, 'article/update.html', context)

