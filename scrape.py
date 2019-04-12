import requests
import pandas as pd
from trello import TrelloClient
from bs4 import BeautifulSoup


def _get_courses():
    page = requests.get('https://www.datacamp.com/courses/all')
    status = str(page.status_code)
    print('Status: ' + status)
    if status != '200':
        return
    soup = BeautifulSoup(page.content, 'html.parser')
    course_blocks = soup.find_all(class_='course-block')
    
    df = pd.DataFrame([], columns=['Name', 'Type', 'Description', 'Link'])
    for course in course_blocks:
        name = str(list(course.children)[1].find(class_='course-block__title').get_text())
        desc = str(list(course.children)[1].find(class_='course-block__description').get_text())[11:].replace('\n', '')
        link = 'https://www.datacamp.com' + str(list(course.children)[1].get('href'))
        type_ = str(list(course.children)[1].find_all('div',
            class_= lambda value: value and value.startswith(
                'course-block__technology'))[0]).replace(
                        '<div class=\"course-block__technology course-block__technology--', '').replace(
                                '\"></div>', '')
                         # Okay, this is pretty bad but it
                         # means I don't have to import re at least

        df = df.append(pd.DataFrame([[name, type_, desc, link]], columns=['Name', 'Type', 'Description', 'Link']))
    return df.reset_index(drop=True)


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
