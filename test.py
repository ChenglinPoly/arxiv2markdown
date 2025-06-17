import asyncio
from crawl4ai import *

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="file:///Users/chenglin/Desktop/research/code/arxiv2markdown/output/2403.16410/2403.16410.html",
        )
        print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())