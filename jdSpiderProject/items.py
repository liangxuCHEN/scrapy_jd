# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class JdspiderprojectItem(scrapy.Item):
    # define the fields for your item here like:
    item_name = scrapy.Field()
    img_url = scrapy.Field()
    price = scrapy.Field()
    item_url = scrapy.Field()
    comment_qty = scrapy.Field()
    shop_url = scrapy.Field()
    shop_name = scrapy.Field()
    page_number = scrapy.Field()
    record_date = scrapy.Field()
    job_id = scrapy.Field()

