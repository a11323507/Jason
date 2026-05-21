import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

def get_image(category, name):
    if "拉麵" in category or "味噌" in category:
        return "https://images.unsplash.com/photo-1557872943-16a5ac26437e?auto=format&fit=crop&w=800&q=80"
    elif "海鮮" in category:
        return "https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?auto=format&fit=crop&w=800&q=80"
    elif "居酒屋" in category:
        return "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=800&q=80"
    elif "蘋果派" in category or "甜點" in category:
        return "https://images.unsplash.com/photo-1562007908-17c67e878c88?auto=format&fit=crop&w=800&q=80"
    elif "自然" in category:
        if "溪" in name or "湖" in name or "池" in name:
            return "https://images.unsplash.com/photo-1437482078695-73f5ca6c96e2?auto=format&fit=crop&w=800&q=80"
        return "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80"
    elif "歷史文化" in category or "巡禮" in category:
        if "溫泉" in name:
            return "https://images.unsplash.com/photo-1584852955513-431d102e3b2b?auto=format&fit=crop&w=800&q=80"
        return "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=800&q=80"
    elif "藝術" in category or "祭典" in category:
        if "美術館" in name:
            return "https://images.unsplash.com/photo-1518998053401-a4149019651c?auto=format&fit=crop&w=800&q=80"
        return "https://images.unsplash.com/photo-1533052402123-951eeec4cce6?auto=format&fit=crop&w=800&q=80"
    return "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=800&q=80"

# Add image field to travelData
def add_image_field(m):
    p1 = m.group(1) # { category: "...",
    p2 = m.group(2) # category
    p3 = m.group(3) # ..., name: "
    p4 = m.group(4) # name
    p5 = m.group(5) # ", ... desc: "..." }
    img_url = get_image(p2, p4)
    return f'{p1}image: "{img_url}", {p3}{p4}{p5}'

html = re.sub(r'(\{ category: "(.*?)", (.*?)name: "(.*?)", (.*?desc: ".*?" \}))', add_image_field, html)

# Replace the inner HTML of the card
old_card_html = r"""card.className = 'glass-panel card-hover rounded-2xl p-6 flex flex-col h-full border-t border-l border-white shadow-sm relative overflow-hidden group cursor-pointer block no-underline';
                
                const iconColor = getCategoryColor(item.category);
                
                card.innerHTML = `
                    <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-gray-100 to-transparent rounded-bl-full opacity-50 group-hover:scale-110 transition-transform duration-300 pointer-events-none"></div>
                    <div class="flex items-start justify-between mb-4 relative z-10">
                        <div class="flex items-center justify-center w-12 h-12 rounded-full text-2xl shadow-inner flex-shrink-0" style="background-color: ${iconColor}20;">
                            ${item.icon}
                        </div>
                        <div class="flex flex-col items-end gap-2">
                            <span class="text-xs font-semibold px-3 py-1 rounded-full border" style="color: ${iconColor}; border-color: ${iconColor}40; background-color: ${iconColor}10;">
                                ${item.category}
                            </span>
                            <span class="text-xs text-gray-500 font-medium flex items-center gap-1 bg-white px-2 py-1 rounded-md shadow-sm border border-gray-100">
                                <svg class="w-3 h-3 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.243-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                                ${item.location}
                            </span>
                            <span class="text-xs text-gray-500 font-medium flex items-center gap-1 bg-white px-2 py-1 rounded-md shadow-sm border border-gray-100">
                                <svg class="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
                                ${item.distance}
                            </span>
                        </div>
                    </div>
                    <h3 class="text-xl font-bold text-gray-800 mb-2 relative z-10 group-hover:text-red-500 transition-colors duration-300">${item.name}</h3>
                    <p class="text-gray-600 text-sm leading-relaxed flex-grow relative z-10">${item.desc}</p>
                    <div class="mt-4 flex items-center text-sm text-blue-500 font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <span>查看相關資訊</span>
                        <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </div>
                `;"""

new_card_html = r"""card.className = 'glass-panel card-hover rounded-2xl flex flex-col h-full border-t border-l border-white shadow-sm relative overflow-hidden group cursor-pointer block no-underline p-0';
                
                const iconColor = getCategoryColor(item.category);
                
                card.innerHTML = `
                    <!-- 圖片區塊 -->
                    <div class="h-48 w-full relative overflow-hidden flex-shrink-0">
                        <img src="${item.image}" alt="${item.name}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500">
                        <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent"></div>
                        <div class="absolute bottom-3 left-4 flex items-center gap-2">
                            <div class="flex items-center justify-center w-10 h-10 rounded-full text-xl shadow-md bg-white/20 backdrop-blur-md border border-white/30">
                                ${item.icon}
                            </div>
                            <span class="text-xs font-semibold px-3 py-1.5 rounded-full text-white bg-white/20 backdrop-blur-md border border-white/30 shadow-sm">
                                ${item.category}
                            </span>
                        </div>
                    </div>
                    
                    <!-- 內文區塊 -->
                    <div class="p-5 flex flex-col flex-grow relative z-10 bg-white/40">
                        <div class="flex flex-wrap gap-2 mb-3">
                            <span class="text-xs text-gray-600 font-medium flex items-center gap-1 bg-white px-2 py-1 rounded-md shadow-sm border border-gray-100">
                                <svg class="w-3 h-3 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.243-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                                ${item.location}
                            </span>
                            <span class="text-xs text-gray-600 font-medium flex items-center gap-1 bg-white px-2 py-1 rounded-md shadow-sm border border-gray-100">
                                <svg class="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
                                ${item.distance}
                            </span>
                        </div>
                        <h3 class="text-xl font-bold text-gray-800 mb-2 group-hover:text-[#E63946] transition-colors duration-300">${item.name}</h3>
                        <p class="text-gray-600 text-sm leading-relaxed flex-grow">${item.desc}</p>
                        <div class="mt-4 flex items-center text-sm text-[#E63946] font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                            <span>查看相關資訊</span>
                            <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        </div>
                    </div>
                `;"""

if old_card_html in html:
    html = html.replace(old_card_html, new_card_html)
else:
    print("WARNING: Could not find the old HTML block perfectly.")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Images and layout updated.")
