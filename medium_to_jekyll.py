#!/usr/bin/env

from lxml import etree
import lxml.html
import html2text
import os
import requests
import shutil
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--author", nargs='?', help="Author Name", default='')
parser.add_argument("-l", "--layout", nargs='?', help="Layout name", default='blog')
parser.add_argument("-cat", "--category", nargs='?', help="Cagegory", default='blog')
parser.add_argument("-src", "--source", help="Medium blog directory", required=True)
parser.add_argument("-dst", "--dest", help="Jekyll blog directory", required=True)

POST_DIRECTORY = '_posts'
IMG_DIRECTORY = 'img'

def usage():
    print 'Usage: %s --source <path-to-medium-articles> --destination <path-to-jekyll-root-directory> --author <author-name> --layout <layout-name> --category <category-name>' % sys.argv[0]

def get_featured_img(doc):
    if not doc.xpath('//img'):
        return ''
    img = doc.xpath('//img')[0]
    url = img.attrib['src']
    return url

def save_images(doc, image_directory):
    for img in doc.xpath('//img'):
        if not 'src' in img.attrib:
            continue
        url = img.attrib['src']
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            filename = url.split('/')[-1]
            filepath = os.path.join(image_directory, filename)
            with open(filepath, 'wb') as w:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, w)
            img.attrib['src'] = '/%s/%s' % ('/'.join(image_directory.split('/')[-2:]), filename)
        else:
            print 'Error processing image (%s): %d' % (url, r.status_code)

def extract_metadata(doc):
    title = etree.tostring(doc.xpath('//title')[0], method='text', encoding='unicode')
    date = doc.xpath('//time/@datetime')[0][:10]
    return title, date

def convert_post(doc):
    drop_xpaths = [
        '//head',
        '//header',
        '//*[contains(@class, "graf--title")]',
        '//section[@data-field="subtitle"]',
        '//footer'
    ]
    for xpath in drop_xpaths:
        elem = doc.xpath(xpath)
        if elem:
            elem[0].drop_tree()
    html = etree.tostring(doc)
    return html2text.html2text(html)

def format_frontmatter(markdown, title, date, author, thumbnail, layout, category):
    post = '---\n'
    post += 'layout:\t"%s"\n' % layout
    post += 'categories:\t"%s"\n' % category
    post += 'title:\t"%s"\n' % title
    post += 'date:\t%s\n' % date
    post += 'thumbnail:\t%s\n' % thumbnail
    post += 'author:\t%s\n' % author
    post += '---\n\n%s' % markdown
    return post

def format_output_filename(filename):
    filename = filename.lower().replace('_', '-')
    return str(filename.split('.')[0]) + '.md'

def main():
    try:
        args = parser.parse_args()
    except SystemExit:
        usage()
        sys.exit(-1)

    medium_directory = args.source
    if not os.path.isdir(medium_directory):
        usage()
        print 'Invalid Medium directory'
        sys.exit(-1)

    jekyll_directory = args.destination
    if not os.path.isdir(jekyll_directory):
        usage()
        print 'Invalid Jekyll directory'
        sys.exit(-1)
    
    author_name = args.author
    layout = args.layout
    category = args.category

    img_directory = os.path.join(jekyll_directory, IMG_DIRECTORY)
    if not os.path.isdir(img_directory):
        os.mkdir(img_directory)
    elif os.path.isfile(img_directory):
        usage()
        print 'Jekyll directory contains `img` file instead of directory'
        sys.exit(-1)

    for filename in os.listdir(medium_directory):
        if filename.startswith('draft') or not filename.endswith('.html'):
            continue
        with open(os.path.join(medium_directory, filename)) as f:
            html = f.read()
            doc = lxml.html.document_fromstring(html)
            title, date = extract_metadata(doc)
            save_images(doc, img_directory)
            markdown = convert_post(doc)
            featured_img = get_featured_img(doc)
            post = format_frontmatter(markdown, title, date, author_name, featured_img, layout, category)
            output_filename = format_output_filename(filename)
            with open(os.path.join(jekyll_directory, POST_DIRECTORY, output_filename), 'w') as out:
                out.write(post.encode('utf-8'))
                print 'Converted %s (Published %s)' % (title, date)

if __name__ == "__main__":
    main()
