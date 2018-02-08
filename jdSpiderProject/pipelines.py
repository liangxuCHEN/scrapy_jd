# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

from jdSpiderProject.db.dbhelper import JdModel, engine
# from scrapy.exceptions import DropItem
from datetime import datetime
import copy


# 存储到数据库
class DataBasePipeline(object):
    def open_spider(self, spider):
        self.items = []
        self.now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def process_item(self, item, spider):
        # item 用的是同一个地址，需要copy才能避免后面的修改
        item['record_date'] = self.now
        #print(item)
        self.items.append(copy.deepcopy(item))

    def close_spider(self, spider):
        conn = engine.connect()
        try:
            conn.execute(JdModel.__table__.insert(), self.items)
        except Exception as e:
            print('插入数据出错， 错误信息：%s' % e)
        finally:
            conn.close()