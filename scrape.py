import requests
import pandas as pd
from trello import TrelloClient
from bs4 import BeautifulSoup
import re


class ScrapeError(Exception):
    pass


def _get_courses_page_content():
    page = requests.get('https://www.datacamp.com/courses/all')
    status = str(page.status_code)
    print('Status: ' + status)
    if status != '200':
        raise ScrapeError(f"Page request returned bad status: {status}")
    else:
        return page.content


def _get_courses(content):
    soup = BeautifulSoup(content, 'html.parser')
    courses_explore_section = soup.find(class_=re.compile('^courses__explore'))
    course_blocks = courses_explore_section.find_all(class_='course-block')
    print(f'{len(course_blocks)} courses found')
    
    data = {}
    for course in course_blocks:
        info_block = course.find(class_=re.compile('^course-block__link'))
        name = info_block.find(class_='course-block__title').get_text()
        desc = info_block.find(class_='course-block__description').get_text(strip=True)
        link = 'https://www.datacamp.com' + info_block.get('href')
        technology_tag = info_block.find('div', class_=re.compile('^course-block__technology'))
        technology = technology_tag.get('class')[1].replace('course-block__technology--','')
        data_id = int(info_block.parent.parent.get('data-id'))
        time = course.find(class_=re.compile('^course-block__length')).get_text(strip=True)
        try:
            author = course.find(class_='course-block__author-name').get_text()
        except AttributeError:
            author = ''

        data[data_id] = [name, technology, desc, link, time, author]

    cols = ['Name', 'Technology', 'Description', 'Link', 'Time', 'Author']

    return pd.DataFrame.from_dict(data, orient='index', columns=cols)


def _get_topics(content):
    soup = BeautifulSoup(content, 'html.parser')
    topic_blocks = soup.find_all(class_='courses__topic')
    print(f'{len(topic_blocks)} topics found')

    topics = []
    for topic in topic_blocks:
        link = 'https://www.datacamp.com' + topic.find(class_='courses__topic-link').get('href')
        title = topic.find(class_='courses__topic-title').get_text()

        topics.append((title, link))

    return topics


def _get_courses_by_topic(topics):

    courses_by_topic = {}

    for topic in topics:
        topic_name, link = topic
        page = requests.get(link)
        status = str(page.status_code)
        print('Status: ' + status)
        if status != '200':
            raise ScrapeError("Page request returned bad status.")

        soup = BeautifulSoup(page.content, 'html.parser')
        courses_explore_section = soup.find(class_=re.compile('^courses__explore'))
        course_blocks = courses_explore_section.find_all(class_='course-block')

        course_names = []
        for course in course_blocks:
            info_block = course.find(class_=re.compile('^course-block__link'))
            name = info_block.find(class_='course-block__title').get_text()
            course_names.append(name)

        courses_by_topic[topic_name] = course_names

    return courses_by_topic


def update_progress():
    return None


def _get_tclient(creds='api.xml'):
    hand = open(creds).read()
    soup = BeautifulSoup(hand, 'lxml')
    client = TrelloClient(
            api_key=soup.find('key').get_text(),
            api_secret=soup.find('secret').get_text(),
            token=soup.find('token').get_text())
    return client


def _add_card(python_list, r_list, other_list, row, board):
    type_ = row['Type']
    L = other_list
    if type_ == 'python':
        L = python_list
    elif type_ == 'r':
        L = r_list

    dupe = False
    for card in board.all_cards():
        if card.name == row['Name']:
            # duplicate so don't add
            dupe = True
    if not dupe:
        L.add_card(row['Name'], row['Description'] + '\n' + row['Link'])


def populate_all_courses(client=_get_tclient()):
    dc_courses_board = None
    for board in client.list_boards():
        if board.name == 'All DC Courses':
            dc_courses_board = board

    lists = dc_courses_board.open_lists()
    python_list = None
    r_list = None
    other_list = None
    for L in lists:
        if L.name == 'Python':
            python_list = L
        elif L.name == 'R':
            r_list = L
        else:
            other_list = L

    for index, row in _get_courses().iterrows():
        print(index)
        _add_card(python_list, r_list, other_list, row, dc_courses_board)


def delete_all_cards(client=_get_tclient()):
    dc_courses_board = None
    for board in client.list_boards():
        if board.name == 'All DC Courses':
            dc_courses_board = board
    for card in dc_courses_board.all_cards():
        print(card)
        card.delete()


def main():
    content = _get_courses_page_content()
    courses = _get_courses(content)
    topics = _get_topics(content)
    courses_by_topic = _get_courses_by_topic(topics)
    courses['Topic'] = courses['Name'].map(
        {course: topic for (topic, courses) in courses_by_topic.items() for course in courses})
    # delete_all_cards()
    # populate_all_courses()
    # update_progress()


if __name__ == '__main__':
    main()
