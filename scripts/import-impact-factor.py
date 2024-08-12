import os
import sys
import pandas as pd
import numpy as np
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from core.models import Journal

if len(sys.argv) != 2:
    print("Usage: python import-impact-factor.py <file>")
    sys.exit(1)

df = pd.read_excel(sys.argv[1])
df.columns = df.columns.str.replace(' ', '')

def convert_value(val):
    if pd.isna(val):
        return val  # NaN 保持不变
    elif val == '<0.1':
        return 0  # 将 "<0.1" 转换为 0
    else:
        return float(val)  # 其余的转换为数字
df['2023最新IF'] = df['2023最新IF'].apply(convert_value)

def process_partition(val):
    if pd.isna(val):
        return val  # NaN 保持不变
    else:
        return val[1]  # 去掉首字母 "Q"，返回第二个字符
df['分区'] = df['分区'].apply(process_partition)

for i, row in df.iterrows():
    impact_factor = row['2023最新IF']
    if pd.isna(impact_factor):
        impact_factor = None
    impact_factor_quartile = row['分区']
    if pd.isna(impact_factor_quartile):
        impact_factor_quartile = None

    Journal(
        name=row['名字'],
        abbreviation=row['缩写'],
        impact_factor=impact_factor,
        impact_factor_year=2023,
        impact_factor_quartile=impact_factor_quartile
    ).save()

    if i % 100 == 0:
        print(f"Importing {i + 1}/{len(df)}...\r", end='')

print(f"Import done. Total {len(df)} journals imported.")
