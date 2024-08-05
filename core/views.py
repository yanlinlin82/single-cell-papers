from collections import Counter
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from core.models import Paper

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
        paper.index = index + 1
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
