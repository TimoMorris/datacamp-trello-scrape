import requests
import pandas as pd
from trello import TrelloClient
from bs4 import BeautifulSoup
import re
from collections import Counter

TOPIC_GROUPS = {
    "Programming": [
        "Programming",
    ],
    "Data": [
        "Importing & Cleaning Data",
        "Data Manipulation",
        "Data Visualization",
    ],
    "Probability & Statistics": [
        "Probability & Statistics",
    ],
    "Machine Learning": [
        "Machine Learning",
    ],
    "Applied": [
        "Applied Finance",
        "Reporting",
        "Case Studies",
    ],
    "Other": [
        "Management",
        "Other",
    ],
}


class ScrapeError(Exception):
    pass


class TopicGroupsError(Exception):
    pass


def _get_page_soup(url):
    """Get HTML soup of the page at the URL.

    Args:
        url: page to be scraped

    Returns:
        BeautifulSoup: HTML soup of the requested page

    Raises:
        ScrapeError: if page request returns bad status

    """
    page = requests.get(url)
    status = page.status_code
    if status != 200:
        raise ScrapeError(f"Page request returned bad status: {status}")
    else:
        return BeautifulSoup(page.content, 'html.parser')


def _scrape_courses(soup):
    """Extract list of courses with info from HTML soup.

    Args:
        soup: HTML soup of page with courses info

    Returns:
        pd.DataFrame: course info in a DataFrame.
            Each row is a course, with DataCamp ID as index,
            and columns:

            * Name
            * Technology
            * Description
            * Link
            * Time
            * Author

    """
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

        data[data_id] = (name, technology, desc, link, time, author)

    cols = ['Name', 'Technology', 'Description', 'Link', 'Time', 'Author']

    return pd.DataFrame.from_dict(data, orient='index', columns=cols)


def _scrape_topics(soup):
    """Extract list of topics with links from HTML soup.

    Args:
        soup: HTML soup of page with topics

    Returns:
        list: of tuples, each corresponding to a topic, of the form:
            (<Topic text title>, <URL of page of courses for that topic>)

    """
    topic_blocks = soup.find_all(class_='courses__topic')
    print(f'{len(topic_blocks)} topics found')

    topics = []
    for topic in topic_blocks:
        link = 'https://www.datacamp.com' + topic.find(class_='courses__topic-link').get('href')
        title = topic.find(class_='courses__topic-title').get_text()

        topics.append((title, link))

    return topics


def _get_courses_by_topic(topics):
    """Get list of courses for each topic.

    Args:
        topics: list of topics, each as tuple of the form:
            (<Topic name>, <URL of page of courses for that topic>)

    Returns:
        dict: mapping topic names to list of courses for that topic

    """

    courses_by_topic = {}

    for (topic, link) in topics:
        soup = _get_page_soup(link)
        courses_explore_section = soup.find(class_=re.compile('^courses__explore'))
        course_blocks = courses_explore_section.find_all(class_='course-block')
        print(f'{topic}: {len(course_blocks)} courses found')

        course_names = []
        for course in course_blocks:
            info_block = course.find(class_=re.compile('^course-block__link'))
            name = info_block.find(class_='course-block__title').get_text()
            course_names.append(name)

        courses_by_topic[topic] = course_names

    return courses_by_topic


def _validate_topic_groups(topic_groups, topics):
    """Verify that the topic groups include each topic, and only once.

    Args:
        topic_groups: groupings of topics,
            dict mapping group name to list of topics
        topics: list of topics found in scraping process

    Raises:
        TopicGroupsError: if topic appears in more than one group,
            or a topic is not assigned to a group

    """
    errors = []
    known_topics = [
        t for (group, topics) in topic_groups.items() for t in topics
    ]

    freqs = Counter(known_topics)
    more_than_once = [topic for (topic, freq) in freqs.items() if freq > 1]
    if more_than_once:
        errors.append(
            f"- topic(s) assigned to more than one group: "
            f"{', '.join(more_than_once)}"
        )

    missing_topics = [t for t in topics if t not in known_topics]
    if missing_topics:
        errors.append(
            f"- topic(s) not assigned to a group: {', '.join(missing_topics)}"
        )

    if errors:
        msg = "Topic groups not valid due to following issue(s):\n"
        msg += "\n".join(errors)
        raise TopicGroupsError(msg)


def _get_list_name(technology, group):
    """Generate name of Trello list for the given course.

    Args:
        technology: technology the course pertains to
        group: group the course is assigned to based on its topic

    Returns:
        str: name of Trello list the given course belongs to

    """
    if technology.lower() not in ['python', 'r']:
        return "Other"
    else:
        return f"{technology.title()} - {group.title()}"


def get_courses():
    """Get DataCamp courses info.

    Returns:
        pd.DataFrame: course info in a DataFrame.
            Each row is a course, with DataCamp ID as index,
            and columns:

            * Name
            * Technology
            * Description
            * Link
            * Time
            * Author
            * Topic
            * Group
            * List

    """
    all_courses_soup = _get_page_soup('https://www.datacamp.com/courses/all')
    courses = _scrape_courses(all_courses_soup)
    topics = _scrape_topics(all_courses_soup)
    courses_by_topic = _get_courses_by_topic(topics)
    courses['Topic'] = courses['Name'].map(
        {course: topic for (topic, courses) in courses_by_topic.items() for course in courses})
    _validate_topic_groups(TOPIC_GROUPS, [t for (t, l) in topics])
    courses['Group'] = courses['Topic'].map(
        {topic: group for (group, topics) in TOPIC_GROUPS.items() for topic in topics})
    courses['List'] = courses.apply(lambda row: _get_list_name(row['Technology'], row['Group']), axis='columns')
    return courses


def update_progress():
    return None


def _get_tclient(creds='api.xml'):
    hand = open(creds).read()
    soup = BeautifulSoup(hand, 'lxml')
    client = TrelloClient(
        api_key=soup.find('key').get_text(),
        api_secret=soup.find('secret').get_text(),
        token=soup.find('token').get_text(),
    )
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

    for index, row in _scrape_courses(_get_page_soup('https://www.datacamp.com/courses/all')).iterrows():
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
    courses = get_courses()
    # delete_all_cards()
    # populate_all_courses()
    # update_progress()


if __name__ == '__main__':
    main()
