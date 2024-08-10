from django.db import models
from django.contrib.auth.models import User

class Paper(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    source = models.CharField(max_length=32, null=True, blank=True, default='')
    parse_time = models.DateTimeField(null=True, blank=True, default=None)

    title = models.CharField(max_length=512)
    journal = models.CharField(max_length=512, null=True, blank=True, default='')
    pub_date = models.CharField(max_length=32, null=True, blank=True, default='')
    pub_date_dt = models.DateField(null=True, blank=True, default=None)
    pub_year = models.IntegerField(null=True, blank=True, default=None)
    doi = models.CharField(max_length=128, null=True, blank=True, default='')
    pmid = models.CharField(max_length=32, null=True, blank=True, default='')
    abstract = models.TextField(null=True, blank=True, default='')

    article_type = models.CharField(max_length=255, null=True, blank=True, default='')
    description = models.CharField(max_length=255, null=True, blank=True, default='')
    novelty = models.CharField(max_length=255, null=True, blank=True, default='')
    limitation = models.CharField(max_length=255, null=True, blank=True, default='')
    research_goal = models.CharField(max_length=255, null=True, blank=True, default='')
    research_objects = models.CharField(max_length=255, null=True, blank=True, default='')
    field_category = models.CharField(max_length=255, null=True, blank=True, default='')
    disease_category = models.CharField(max_length=255, null=True, blank=True, default='')
    technique = models.CharField(max_length=255, null=True, blank=True, default='')
    model_type = models.CharField(max_length=255, null=True, blank=True, default='')
    data_type = models.CharField(max_length=255, null=True, blank=True, default='')
    sample_size = models.CharField(max_length=255, null=True, blank=True, default='')

    def __str__(self):
        return f"{self.pub_year} - {self.journal} - {self.title}"

class Payment(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    openid = models.CharField(max_length=128, null=True, blank=True)
    order_number = models.CharField(max_length=64, unique=True, null=True, blank=True, default=None)
    has_paid = models.BooleanField(default=False)
    paid_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, default=None)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_callback = models.TextField(null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.user.username} - {'Paid' if self.has_paid else 'Not Paid'}"
