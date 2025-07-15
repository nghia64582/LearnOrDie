import os

def download_and_extract_wiki(output_file="big_corpus.txt"):
    os.system("wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2")
    os.system("wikiextractor enwiki-latest-pages-articles.xml.bz2 -o extracted --json")

    with open(output_file, 'w', encoding='utf-8') as out:
        for root, _, files in os.walk("extracted"):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                import json
                                data = json.loads(line)
                                out.write(data.get("text", "") + "\n")
                            except:
                                pass

download_and_extract_wiki()
