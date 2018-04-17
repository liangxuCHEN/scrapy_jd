from scrapy import Request
from scrapy.spiders import Spider
from jdSpiderProject.items import JdspiderprojectItem
from datetime import datetime

from jdSpiderProject.db.dbhelper import engine, JdProjectModel
from sqlalchemy.orm import sessionmaker



Session_Class = sessionmaker(bind=engine)  # 创建与数据库的会话，Session_Class为一个类

Session = Session_Class()  # 实例化与数据库的会话

"""
需要查找信息列表

参数说明：

id: 这个搜索项目的ID,（TODO：以后在数据库生成）
market：京东
key_word: 输入搜索框的关键字
page_number： 需要爬取的页数，最大100页
min_price： 选填，搜索得到宝贝价格的最低价
max_price: 选填，搜索得到宝贝价格的最高价
project_name: 项目名称
"""
# TODO:数据库获取新项目
# search_parameter = [
#     {'project_name':'201803290B', 'market': '京东', 'min_price':'', 'max_price':'', 'key_word': '乳胶床垫', 'page_number': 5}
# ]

def get_project():
    entity = Session.query(JdProjectModel).filter(
        (JdProjectModel.status=='new') & 
        (JdProjectModel.market=='京东')).all()
    return [e.to_json() for e in entity]

class JDSpider(Spider):
    name = 'JDSpider'
    search_url = 'https://search.jd.com/s_new.php?keyword={key}' \
                '&enc=utf-8&qrst=1&rt=1&stop=1&vt=2&offset=3&wq={key}&page={page}' \
                '&s=26&scrolling=y&pos=30&show_items={items}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
    }

    start_url = 'https://search.jd.com/Search?keyword={key}&enc=utf-8&qrst=1&rt=1' \
                '&stop=1&vt=2&offset=5&wq={key}&page={page}'

    allowed_domains = ["jd.com"]

    def start_requests(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        search_parameter = get_project()
        for data in search_parameter:
            # 把项目添加到数据库
            # TODO: 如果在数据库拿的项目就是update
            jd_project = Session.query(JdProjectModel).filter_by(id=data['id']).first()
            jd_project.status = 'running'
            Session.commit()

            for i in range(1 , data['page_number']):
                page=i*2-1  # 这里是构造请求url的page,表示奇数
                url=self.start_url.format(key=data['key_word'], page=str(page))
                # 这里使用meta想回调函数传入数据，回调函数使用response.meta['search-page']接受数据
                yield Request(url,
                              meta={
                                  'search_page':page,
                                  'key_word': data['key_word'],
                                  'job_id': data['project_name']
                              },
                              callback= self.parse_url)

            # 更新状态
            jd_project.status = 'finish'
            Session.commit()

    def parse_url(self,response):
        if response.status==200:   #判断是否请求成功

            # print(response.url)
            # 这个集合用于过滤和保存得到的id,用于作为后面的ajax请求的url构成
            get_pids = set()

            #try:
                # 首先得到所有衣服的整个框架，然后从中抽取每一个框架
            all_goods = response.xpath("//div[@id='J_goodsList']/ul/li")

            for goods in all_goods:
                #从中解析每一个
                # 这是一个调试的方法，这里会直接打开调试模式
                # scrapy.shell.inspect_response(response,self)
                items = JdspiderprojectItem()   #定义要抓取的数据

                # 所在页面
                items['page_number'] = response.meta['search_page']
                items['job_id'] = response.meta['job_id']

                # 如果不存在就是一个空数组[]，因此不能在这里取[0]
                img_url_src = goods.xpath("div/div[1]/a/img/@src").extract()
                img_url_delay = goods.xpath(
                    "div/div[1]/a/img/@data-lazy-img").extract()
                # 这个是没有加载出来的图片，这里不能写上数组取第一个[0]
                #price = goods.xpath("div/div[2]/strong/i/text()").extract()  #价格
                price = goods.xpath("div/div[3]/strong/i/text()").extract()
                item_name = goods.xpath("div/div[4]/a/em/text()").extract()
                #item_name = goods.xpath("div/div[3]/a/em/text()").extract()
                shop_id = goods.xpath("div/div[7]/@ data-shopid").extract()
                #item_url = goods.xpath("div/div[3]/a/@href").extract()
                item_url = goods.xpath("div/div[1]/a/@href").extract()
                #comment_qty = goods.xpath("div/div[4]/strong/a/text()").extract()
                comment_qty = goods.xpath("div/div[5]/strong/a/text()").extract()
                pid = goods.xpath("@data-pid").extract()
                # product_id=goods.xpath("@data-sku").extract()//
                #shop_name = goods.xpath("div/div[5]/span/a/text()").extract()
                shop_name = goods.xpath("div/div[7]/span/a/text()").extract()
                #shop_url = goods.xpath("div/div[5]/span/a/@href").extract()
                shop_url = goods.xpath("div/div[7]/span/a/@href").extract()
                if get_pids:
                    get_pids.add(pid[0])
                if img_url_src:  # 如果img_url_src存在
                    items['img_url'] = img_url_src[0]
                if img_url_delay:  # 如果到了没有加载完成的图片，就取这个url
                    items['img_url'] = img_url_delay[0]  # 这里如果数组不是空的，就能写了
                else:
                    items['img_url'] = ''

                if price:
                    items['price'] = price[0]
                else:
                    items['price'] = 0

                if item_name:
                    items['item_name'] = ''.join(item_name)
                else:
                    items['item_name'] = ''

                # 店铺名字
                if shop_id:
                    #items['shop_id'] = shop_id[0]
                    shop_url = "https://mall.jd.com/index-" + str(shop_id[0]) + ".html"
                    #shop_url = "https:"+ shop_url[0]
                    items['shop_url'] = shop_url
                else:
                    print('xxxxxxxx', shop_url)
                    items['shop_url'] = "https:"+ shop_url[0]

                if shop_name:
                    items['shop_name'] = shop_name[0]
                else:
                    items['shop_name'] = ''

                if item_url:
                    items['item_url'] = item_url[0]
                else:
                    items['item_url'] = ''

                print('!!!!!!!!!!!!!', comment_qty)
                if comment_qty:
                    if '万' in comment_qty[0]:
                        items['comment_qty'] = str(int(float(comment_qty[0][:-2]) * 10000))
                    elif len(comment_qty[0]) > 1:
                        items['comment_qty'] = comment_qty[0][:-1]
                    else:
                        items['comment_qty'] = comment_qty[0]
                else:
                    items['comment_qty'] = '-1'

                # if product_id:
                # 进一步爬取页面信息
                #     print "******************进一步爬取页面信息*******************"
                #     print self.comments_url.format(str(product_id[0]),str(self.count))
                #     yield scrapy.Request(url=self.comments_url.format(str(product_id[0]),str(self.count)),callback=self.comments)
                #yield scrapy.Request写在这里就是每解析一个键裤子就会调用回调函数一次
                print('#############',items['comment_qty'])
                yield items
            # except Exception as e:
            #     print("******************ERROR***************")
            #     print(e)
            # 再次请求，这里是请求ajax加载的数据，必须放在这里，因为只有等到得到所有的pid才能构成这个请求，回调函数用于下面的解析
            yield Request(
                url=self.search_url.format(
                    key=response.meta['key_word'],
                    page=str(response.meta['search_page']+1),
                    items=",".join(get_pids)),
                meta={
                    'search_page': response.meta['search_page']+1,
                    'job_id': response.meta['job_id'],
                },
                callback=self.next_half_parse)


    def next_half_parse(self, response):
        if response.status == 200:
            # print(response.url)
            items = JdspiderprojectItem()
            # scrapy.shell.inspect_response(response,self)    #y用来调试的
            #try:
            lis = response.xpath("//li[@class='gl-item']")
            for li in lis:
                img_url_1 = li.xpath("div/div[1]/a/img/@src").extract()
                img_url_2 = li.xpath("div/div[1]/a/img/@data-lazy-img").extract()
                
                #version 2
                #price = li.xpath("div/div[2]/strong/i/text()").extract()  #价格
                #item_name = li.xpath("div/div[3]/a/em/text()").extract()

                price = li.xpath("div/div[3]/strong/i/text()").extract()
                item_name = li.xpath("div/div[4]/a/em/text()").extract()

                shop_id = li.xpath("div/div[7]/@ data-shopid").extract()
                #item_url = li.xpath("div/div[3]/a/@href").extract()
                item_url = li.xpath("div/div[1]/a/@href").extract()
                #comment_qty = goods.xpath("div/div[4]/strong/a/text()").extract()
                comment_qty = li.xpath("div/div[5]/strong/a/text()").extract()
                #comment_qty = li.xpath("div/div[4]/strong/a/text()").extract()
                pid = li.xpath("@data-pid").extract()
                # product_id=goods.xpath("@data-sku").extract()//
                #shop_name = li.xpath("div/div[5]/span/a/text()").extract()
                shop_name = li.xpath("div/div[7]/span/a/text()").extract()
                #shop_url = li.xpath("div/div[5]/span/a/@href").extract()
                shop_url = li.xpath("div/div[7]/span/a/@href").extract()
                items['page_number'] = response.meta['search_page']
                items['job_id'] = response.meta['job_id']

                if item_url:
                    items['item_url'] = item_url[0]
                else:
                    items['item_url'] = ''

                if img_url_1:
                    items['img_url'] = img_url_1[0]
                if img_url_2:
                    items['img_url'] = img_url_2[0]
                else:
                    items['img_url'] = ''

                if item_name:
                    #items['item_name'] = ''.join(item_name)
                    items['item_name'] = item_name[0]
                else:
                    items['item_name'] = ''

                if price:
                    items['price'] = price[0]
                else:
                    items['price'] = 0

                if shop_id:
                    # items['shop_id'] = shop_id[0]
                    items['shop_url'] = "https://mall.jd.com/index-" + str(shop_id[0]) + ".html"
                else:
                    print('xxxxxxx', shop_url)
                    items['shop_url'] = "https:"+ shop_url[0]

                if shop_name:
                    items['shop_name'] = shop_name[0]
                else:
                    items['shop_name'] = ''

                if comment_qty:
                    if '万' in comment_qty[0]:
                        items['comment_qty'] = str(int(float(comment_qty[0][:-2]) * 10000))
                    elif len(comment_qty[0]) > 1:
                        items['comment_qty'] = comment_qty[0][:-1]
                    else:
                        items['comment_qty'] = comment_qty[0]
                else:
                    items['comment_qty'] = '-1'
                # 又一次的生成，这里是完整的数据，因此可以yield items
                print('############',items['comment_qty'])
                yield items
            # except Exception as e:
            #     print("*****error******")
            #     print(e)