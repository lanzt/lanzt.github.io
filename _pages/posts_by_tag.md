---
layout: page
title: Los tagtequieto
permalink: /tags
---

🙏 Gracias [github/cagrimmett/jekyll-tools](https://github.com/cagrimmett/jekyll-tools#posts-by-tag), ta guapetón.

**Acá están listados los tags de toooooodos los posts del blog, solo que relacionamos que artículos se enfocan en X tag.**

{% assign sorted_tags = (site.tags | sort:0) %}
<ul class="tag-box">
	{% for tag in sorted_tags %}
		{% assign t = tag | first %}
		{% assign posts = tag | last %}
		<li><a href="#{{ t }}">{{ t }} <span class="size">({{ posts.size }})</span></a></li>
	{% endfor %}
</ul>

{% for tag in sorted_tags %}
  {% assign t = tag | first %}
  {% assign posts = tag | last %}

<h4 id="{{ t }}">{{ t }}</h4>
<ul>
{% for post in posts %}
  {% if post.tags contains t %}
    <li>
      <span class="date">{{ post.date | date: '%d %b %y' }}</span>:  <a href="{{ post.url }}">{{ post.title }}</a>
    </li>
  {% endif %}
{% endfor %}
</ul>
{% endfor %}

...

