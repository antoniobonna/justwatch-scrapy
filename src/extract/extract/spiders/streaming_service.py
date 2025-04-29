import scrapy
from scrapy_playwright.page import PageMethod


class StreamingServiceSpider(scrapy.Spider):
    name = "streaming_service"
    allowed_domains = ["www.justwatch.com"]
    base_url = "https://www.justwatch.com/br/provedor"
    provedores = [
        "disney-plus",
        "netflix",
        "amazon-prime-video",
        "max",
        "paramount-plus",
        "apple-tv-plus",
        "globoplay",
    ]

    # filmes ou series
    categoria = [
        "filmes",
        "series"
    ]

    def start_requests(self):
        for provedor in ["apple-tv-plus"]:
            for categoria in ["filmes"]:
                yield scrapy.Request(
                    url=f"{self.base_url}/{provedor}/{categoria}",
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "div.title-list-grid__item"),
                        ],
                        "provedor": provedor,
                        "categoria": categoria
                    },
                    callback=self.parse,
                )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        provedor = response.meta["provedor"]
        categoria = response.meta["categoria"]

        # Configurações para rolagem infinita
        max_scrolls = 150  # Número máximo de tentativas de rolagem
        scroll_delay = 1500  # Tempo de espera após cada rolagem (ms)

        # Contadores para monitorar novos itens
        previous_item_count = 0
        scroll_count = 0

        # Obter contagem inicial de itens
        items = await page.query_selector_all("div.title-list-grid__item")
        current_item_count = len(items)

        # Loop de rolagem usando while
        while current_item_count > previous_item_count and scroll_count < max_scrolls:
            # Registrar contagem anterior
            previous_item_count = current_item_count

            # Executar scroll até o final da página
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Esperar o carregamento de novos itens
            await page.wait_for_timeout(scroll_delay)

            # Atualizar contagem de itens
            items = await page.query_selector_all("div.title-list-grid__item")
            current_item_count = len(items)

            # Incrementar contador de scrolls
            scroll_count += 1

            # Se a contagem não mudar, incrementar contador de tentativas sem novos itens
            if current_item_count == previous_item_count:
                break

        # Visitar cada item para coletar detalhes
        for item in items:
            link_element = await item.query_selector("a")
            href = await link_element.get_attribute("href")

            url = response.urljoin(href)

            yield scrapy.Request(
                url=url,
                callback=self.parse_item,
                meta={
                    "provedor": provedor,
                    "categoria": categoria
                }
            )

        # Fechar a página do Playwright
        await page.close()

    def parse_item(self, response):
        provedor = response.meta["provedor"]
        categoria = response.meta["categoria"]
        titulo = response.css("h1.title-detail-hero__details__title::text").get()
        ano = response.css("span.release-year::text").get()
        duracao = response.css("div.title-detail-hero-details__item::text")[-1].get()
        imdb_score = response.css("span.imdb-score::text").get()
        classificacao = response.css("#age-rating-popover").xpath('./ancestor::div[@class="title-detail-hero-details__item"]/text()').get()
        sinopse = response.css("div#synopsis p::text").get()

        yield {
            "provedor": provedor,
            "categoria": categoria,
            "titulo": titulo,
            "ano": ano,
            "duracao": duracao,
            "imdb_score": imdb_score,
            "classificacao": classificacao,
            "sinopse": sinopse,
        }
