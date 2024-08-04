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

    query = request.GET.get('q')
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

    papers = papers.order_by('-created')

    page_number = request.GET.get('page')
    papers, items = get_paginated_reviews(papers, page_number)

    for index, paper in enumerate(papers):
        paper.index = index + 1
    return render(request, 'core/home.html', {
        'query': query,
        'papers': papers,
        'items': items,
    })
