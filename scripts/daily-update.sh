#!/bin/bash

APP_NAME=$(basename $(pwd))
echo "========== $(date) =========="
echo ">>> Updating for $APP_NAME"

if [ ! -d pubmed/updatefiles/ ]; then
    echo "ERROR: Directory 'pubmed/updatefiles/' does not exist!"
    exit 1
fi

BAK_FILE=db.sqlite3.bak-$(date +%Y%m%d)
if [ -e "${BAK_FILE}" ]; then
	echo ">>> It has been updated already today"
	exit 0
fi
cp -av db.sqlite3 ${BAK_FILE}

PUBMED_XML_GZ=$(find pubmed/updatefiles/ -type f -name '*.xml.gz' | sort | tail -n1)
if [ -z "${PUBMED_XML_GZ}" ]; then
    echo "ERROR: No PubMed XML file found in 'pubmed/updatefiles/'!"
    exit 1
fi
echo ">>> Latest PubMed XML file: $PUBMED_XML_GZ"

SOURCE=$(basename $PUBMED_XML_GZ .xml.gz)
SOURCE=${SOURCE#pubmed24n}
echo ">>> Got source: $SOURCE"

mkdir -pv log/pubmed
.venv/bin/python scripts/scan-pubmed.py $PUBMED_XML_GZ >>log/pubmed/${SOURCE}.log 2>&1

tail -n1 log/pubmed/${SOURCE}.log
echo ">>> Updating for $APP_NAME done"
