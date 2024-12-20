Task Examples
===========

This guide provides examples of different task implementations in NewLoom.

Article Search Task
----------------

Example implementation of an article search task:

.. code-block:: python

    def search_articles(stream_id, url, link_selector, search_text, article_selector,
                       link_selector_type="css", article_selector_type="css", max_links=10):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = context.new_page()
            
            try:
                stealth_sync(page)
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)

                # Get base URL for handling relative URLs
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                # Get links using appropriate selector method
                elements = (page.query_selector_all(link_selector) 
                          if link_selector_type == "css"
                          else page.locator(f"xpath={link_selector}").all())

                matching_links = []
                for element in elements[:max_links]:
                    href = element.get_attribute("href")
                    title = element.evaluate("el => el.textContent")
                    
                    if href:
                        full_url = urljoin(base_url, href)
                        # Visit each link and search for text
                        page.goto(full_url, timeout=60000)
                        article_content = (page.query_selector(article_selector)
                                        if article_selector_type == "css"
                                        else page.locator(f"xpath={article_selector}").first)
                        
                        if article_content and search_text.lower() in article_content.text_content().lower():
                            matching_links.append({
                                "url": full_url,
                                "title": title.strip() if title else None
                            })
                            
            finally:
                browser.close()

        return matching_links

News Stream Task
-------------

Example of a news stream processing task using AI:

.. code-block:: python

    def process_news_stream(stream_id, agent_id, time_window_minutes=60, 
                          max_items=100, save_to_docs=True):
        # Get the stream and agent
        stream = Stream.objects.get(id=stream_id)
        agent = Agent.objects.get(id=agent_id)

        # Get recent news items
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        news_items = News.objects.filter(
            source__in=stream.media.sources.all(),
            created_at__gte=time_threshold
        ).order_by("-created_at")[:max_items]

        # Get examples for the media
        examples = Examples.objects.filter(media=stream.media)
        examples_text = "\n\n".join(example.text for example in examples)

        # Join news items
        news_content = "\n\n---\n\n".join(
            f"Title: {news.title}\n\nContent: {news.text}\n\nURL: {news.link}"
            for news in news_items
        )

        # Process with AI
        response = invoke_bedrock_anthropic(
            system_prompt=agent.system_prompt.format(
                news=news_content,
                examples=examples_text,
                now=timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            user_prompt=agent.user_prompt_template.format(
                news=news_content,
                examples=examples_text,
                now=timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        # Save results
        if save_to_docs:
            result = json.loads(response["completion"])
            for post in result.get("posts", []):
                Doc.objects.create(
                    media=stream.media,
                    link=post.get("url", ""),
                    title=result.get("topic", "Untitled"),
                    text=post.get("text", ""),
                    status="new"
                )

Telegram Task
-----------

Example of a Telegram channel monitoring task:

.. code-block:: python

    def monitor_telegram_channel(stream_id, posts_limit=20):
        stream = Stream.objects.get(id=stream_id)
        source = stream.source

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                stealth_sync(page)
                page.goto(source.url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)

                posts = []
                while len(posts) < posts_limit:
                    message_elements = page.query_selector_all(
                        "div.tgme_widget_message_wrap"
                    )

                    for message_element in message_elements:
                        # Extract message details
                        text_element = message_element.query_selector(
                            "div.tgme_widget_message_text"
                        )
                        link_element = message_element.query_selector(
                            "a.tgme_widget_message_date"
                        )
                        time_element = message_element.query_selector("time")

                        if all([text_element, link_element, time_element]):
                            message_text = text_element.inner_text().strip()
                            message_link = link_element.get_attribute("href")
                            datetime_str = time_element.get_attribute("datetime")
                            message_time = datetime.fromisoformat(
                                datetime_str.replace("Z", "+00:00")
                            )

                            # Save to database
                            News.objects.get_or_create(
                                source=source,
                                link=message_link,
                                defaults={
                                    "text": message_text,
                                    "published_at": message_time
                                }
                            )
                            posts.append({
                                "text": message_text,
                                "link": message_link,
                                "timestamp": message_time
                            })

                    # Scroll for more posts if needed
                    if len(posts) < posts_limit:
                        page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight);"
                        )
                        page.wait_for_timeout(2000)

            finally:
                browser.close()

        return posts

These examples demonstrate the current implementation patterns used in NewLoom, including:

* Playwright for web automation and scraping
* Django ORM for database operations
* Async/await patterns for Telegram operations
* Integration with AI services (Amazon Bedrock)
* Error handling and logging
* Resource cleanup

The tasks follow a consistent pattern of:
1. Getting configuration from the stream
2. Performing the main task operation
3. Saving results to the database
4. Proper error handling and cleanup
