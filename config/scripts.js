// Зумирование jpg в правой части страницы

document.addEventListener('DOMContentLoaded', function () {
    // Автоматическая настройка высоты textarea
    document.querySelectorAll('textarea').forEach(function(textarea) {
        textarea.style.height = textarea.scrollHeight + 'px';
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });
	
    const rightPane = document.querySelector('.right-pane');
    if (rightPane) {
        rightPane.style.userSelect = 'none'; // Предотвращаем выделение текста внутри .right-pane
    }

    const img = document.querySelector('.right-pane img');
    if (img) {
        let scale = 1;
        let isDragging = false;
        let startX, startY;

        img.addEventListener('mousedown', (e) => {
            if (scale > 1) {
                isDragging = true;
                startX = e.pageX - img.offsetLeft;
                startY = e.pageY - img.offsetTop;
                img.style.cursor = 'grabbing';
                e.preventDefault(); // Предотвращаем выделение текста
            }
        });

        img.addEventListener('mouseleave', () => {
            isDragging = false;
            img.style.cursor = scale > 1 ? 'move' : 'grab';
        });

        img.addEventListener('mouseup', () => {
            isDragging = false;
            img.style.cursor = scale > 1 ? 'move' : 'grab';
        });

        img.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const x = e.pageX - startX;
            const y = e.pageY - startY;
            img.style.left = `${x}px`;
            img.style.top = `${y}px`;
        });

        img.addEventListener('wheel', (e) => {
            e.preventDefault(); // Предотвращаем прокрутку страницы при зумировании
            if (e.deltaY > 0) {
                // Zoom out
                scale = Math.max(1, scale - 0.2);
            } else {
                // Zoom in
                scale += 0.2;
            }
            img.style.transform = `scale(${scale})`;
            img.style.cursor = scale > 1 ? 'move' : 'grab';
            img.style.position = 'relative';
        });
		
		const centerImage = () => {
            const containerWidth = img.parentElement.clientWidth;
            const containerHeight = img.parentElement.clientHeight;
            const imgWidth = img.clientWidth * scale;
            const imgHeight = img.clientHeight * scale;
            const offsetX = (containerWidth - imgWidth) / 2;
            const offsetY = (containerHeight - imgHeight) / 2;
            img.style.left = `${offsetX}px`;
            img.style.top = `${offsetY}px`;
			img.style.transition = 'left 0.5s, top 0.5s'; // Плавность центрирования
            img.style.left = `${offsetX}px`;
            img.style.top = `${offsetY}px`;
			
			// Удаление transition после завершения анимации
            setTimeout(() => {
                img.style.transition = '';
            }, 500);
        };

        img.addEventListener('dblclick', () => {
            if (scale === 1) {
                scale = 2; // Двойной зум
            } else {
                scale = 1; // Обратное действие
                setTimeout(centerImage, 500); // Центрирование изображения
            }
            img.style.transform = `scale(${scale})`;
            img.style.cursor = scale > 1 ? 'move' : 'grab';
            img.style.position = 'relative';
        });
    }
});





// Сохранение json файла с внесенными изменениями

document.getElementById('save-button').addEventListener('click', generateJSON);

function generateJSON() {
    // Получаем строку JSON из скрытого div
    var originalJsonString = document.getElementById('jsonfiledataid').textContent;

    try {
        // Преобразуем строку JSON в объект JavaScript
        var originalJsonObject = JSON.parse(originalJsonString);

        // Получаем значения всех редактируемых полей
        var form = document.querySelector('form');
        var formData = new FormData(form);
        var values = [];
        formData.forEach(value => values.push(value));

        // Функция для рекурсивного создания объекта с нулевыми значениями
        function setValuesFromArray(obj, values) {
            let index = 0;
            function recurse(obj) {
                if (Array.isArray(obj)) {
                    return obj.map(recurse);
                } else if (typeof obj === 'object' && obj !== null) {
                    const newObj = {};
                    for (const key in obj) {
                        newObj[key] = recurse(obj[key]);
                    }
                    return newObj;
                } else {
                    return values[index++];
                }
            }
            return recurse(obj);
        }
		
		function getCurrentTime() {
            // Получаем текущее время в миллисекундах с начала эпохи
            const milliseconds = Date.now().toString().slice(-11);
            return milliseconds;
        }

        // Создаем новый объект с значениями из редактируемых полей
        var generatedJsonObject = setValuesFromArray(originalJsonObject, values);

        // Преобразуем объект обратно в строку JSON
        var generatedJsonString = JSON.stringify(generatedJsonObject, null, 4);

        // Сохраняем JSON строку как текстовый файл
        var blob = new Blob([generatedJsonString], { type: 'application/json' });
        var link = document.createElement('a');
		
		var currentTime = getCurrentTime();
		var originalFilename = document.getElementById('jsonfilenameid').getAttribute('jsonfilename');

		// 11 знаков (временная отметка)  + 1 "_" + 5 ".json" = 17 знаков
		var newFilename = originalFilename.slice(0, -17) + `_${currentTime}.json`;
		
        link.href = URL.createObjectURL(blob);
        link.download = newFilename;
        link.click();
    } catch (error) {
        // В случае ошибки выводим сообщение об ошибке
        alert("Произошла ошибка: " + error.message);
    }
}