import requests
import pandas as pd
from trello import TrelloClient
from bs4 import BeautifulSoup
import re


def _get_courses():
    page = requests.get('https://www.datacamp.com/courses/all')
    status = str(page.status_code)
    print('Status: ' + status)
    if status != '200':
        return
    soup = BeautifulSoup(page.content, 'html.parser')
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
    # delete_all_cards()
    # populate_all_courses()
    # update_progress()
    # _get_courses()
    exit(0)


if __name__ == '__main__':
    main()
