# -*- coding: UTF-8 -*-

import requests
import re
import json
import sys
import time
reload(sys)
sys.setdefaultencoding("utf-8")

# 对于图集，只能取到第一张图的url，若要取后续的图片，需要对每个图集进行一次请求，代价比较大，所以没做

class InsTagCrawler:
    def __init__(self, tag):
        str(time.time())
        self.tag = tag
        self.filename = tag + '_' + str(int(time.time())) + '.txt'    # 存结果的文件路径

    # max_count 为想要获取的最大post数
    def get_posts_by_tag(self, max_count):
        # 第一次请求的数据来自于HTML源代码
        url = 'https://www.instagram.com/explore/tags/' + self.tag + '/'
        response = requests.get(url=url, verify=False)
        page = response.text
        pattern = re.compile("window._sharedData = (.*?);</script>", re.S)
        items = re.findall(pattern, page)
        data = json.loads(items[0])

        hash_tag = data['entry_data']['TagPage'][0]['graphql']['hashtag']
        top_posts = hash_tag['edge_hashtag_to_top_posts']['edges']  # 前9条热门 post
        media_data = hash_tag['edge_hashtag_to_media']
        recent_posts = media_data['edges']
        total_count = media_data['count']   #post 总数
        print self.tag + ' 话题下共有 ' + str(total_count) + ' 个 post'

        has_next_page = media_data['page_info']['has_next_page']
        end_cursor = media_data['page_info']['end_cursor']

        post_list = []
        post_list.extend(self.extract_list(top_posts))
        post_list.extend(self.extract_list(recent_posts))

        # 后续的数据来自于接口
        while len(post_list) < max_count and has_next_page:
            # 若出现返回错误， 可以尝试休眠
            try:
                response = self.request_api(end_cursor)
                media_data = json.loads(response)['data']['hashtag']['edge_hashtag_to_media']
                post_list.extend(self.extract_list(media_data['edges']))
                has_next_page = media_data['page_info']['has_next_page']
                end_cursor = media_data['page_info']['end_cursor']
            except:
                time.sleep(60)   # 可以根据实际情况调整休眠时间 单位 秒
                continue

        post_list = post_list[0:max_count]
        self.sort(post_list, 'like')

        # 如果程序没有中断，把排序后的结果覆盖写入
        self.write_result(self.filename, post_list)


    # 过滤掉 video post
    def filter_video(self, post_list):
        return list(filter(lambda x: not x['node']['is_video'], post_list))


    # 处理 post_list
    def extract_list(self, post_list):
        # 过滤掉 video post
        post_list = self.filter_video(post_list)
        result = []
        for post in post_list:
            post_dict = self.extract_post(post)
            result.append(post_dict)
            post_str = json.dumps(post_dict)
            print post_str
            self.write_file_add(self.filename, post_str)
        return result


    # 提取 post 信息
    def extract_post(self, post):
        node = post['node']
        temp = {
            'ins_url': 'https://www.instagram.com/p/' + node['shortcode'] + '/',
            'comment': node['edge_media_to_comment']['count'],
            'like': node['edge_media_preview_like']['count'],
            'img_url': node['display_url']
        }
        return temp

    # 程序最终结束时，把所有post覆盖写入文件
    def write_result(self,filename, post_list):
        content = ''
        for post in post_list:
            content += json.dumps(post) + '\n'
        self.write_file_override(self.filename, content)


    # 追加写入文件
    def write_file_add(self, filename, content):
        with open(filename, 'a+') as file:
            file.write(content + '\n')


    # 覆盖写入文件
    def write_file_override(self, filename, content):
        with open(filename, 'w+') as file:
            file.write(content + '\n')


    # 按照字段排序  key = like|comment
    def sort(self, post_list, key='like'):
        return post_list.sort(key=lambda x:x[key], reverse=True)


    def request_api(self, end_cursor):
        url = 'https://www.instagram.com/graphql/query/'
        variables = {
            'tag_name': self.tag,
            'first': 100,   # 不是严格的返回post数量，但经测试，first越大，返回的post越多，100已是上限
            'after': end_cursor
        }
        params = {
            'query_hash': '1780c1b186e2c37de9f7da95ce41bb67',   # 固定不变
            'variables': json.dumps(variables)
        }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'cookie': 'mid=W3KH6wAEAAF5sYu9JNP_Xbj1Q3PQ; mcd=3; csrftoken=TAELP53Sc2zeYnAjsikeI5CaPUpxR7KP; ds_user_id=3655666981; csrftoken=TAELP53Sc2zeYnAjsikeI5CaPUpxR7KP; ig_cb=1; shbid=12530; sessionid=IGSCa8daf282b443ecf659122290e301d80487ae3cef112426103673467b5481c5b9%3ABXFCY7Hksf5GbZ2aN4Niw0os7Fy8XCAd%3A%7B%22_auth_user_id%22%3A3655666981%2C%22_auth_user_backend%22%3A%22accounts.backends.CaseInsensitiveModelBackend%22%2C%22_auth_user_hash%22%3A%22%22%2C%22_platform%22%3A4%2C%22_token_ver%22%3A2%2C%22_token%22%3A%223655666981%3AU8TQBejePEPPpgii11hZc0cU6S3nQLxW%3Afd233bdc5e0fe4e3267233ed38f2511b4494b8c3cfbbb0f1edf963bc0f049936%22%2C%22last_refreshed%22%3A1537257954.8267505169%7D; shbts=1537324199.0074363; rur=FTW; urlgen="{\"103.206.189.72\": 136993}:1g2SQF:aSo6fgj1x-ikQlA9JG1z6QXGpdU"',
            'pragma': 'no-cache',
            'pgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
        }

        response =  requests.get(url, params=params, headers=headers)
        # print response.url
        return response.text


if __name__ == '__main__':
    crawler = InsTagCrawler('surf')
    # 获取1000个post
    crawler.get_posts_by_tag(1000)