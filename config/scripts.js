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


// --------------------------------------------------------------------------------------------------------------------
// Сохранение json файла с внесенными изменениями
/*
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
*/
// --------------------------------------------------------------------------------------------------------------------
// Добавить новую услугу

function addService(button) {
    var fieldset = button.parentElement;
    var services = fieldset.querySelectorAll('fieldset');

    if (services.length === 0) return;

    var firstService = services[0];
    var newService = firstService.cloneNode(true);

    var inputs = newService.querySelectorAll('input, textarea');
    inputs.forEach(function(input) {
        if (input.type === 'checkbox') {
            input.checked = false;
        } else {
            input.value = '';
        }
    });

    var lastService = services[services.length - 1];
    var lastLegend = lastService.querySelector('legend');
    var newLegendNumber = parseInt(lastLegend.innerText) + 1;

    var newLegend = newService.querySelector('legend');
    newLegend.innerText = newLegendNumber;

    fieldset.insertBefore(newService, button);

    // Вызов функции dropdownService1C после добавления нового service
    dropdownService1C();
}


// --------------------------------------------------------------------------------------------------------------------
// Удалить последнюю услугу

function removeService(button) {
    var fieldset = button.parentElement;
    var services = fieldset.querySelectorAll('fieldset');

    if (services.length > 1) {
        var lastService = services[services.length - 1];
        fieldset.removeChild(lastService);
    } else {
        alert("Нельзя удалить единственную услугу.");
    }
}


// --------------------------------------------------------------------------------------------------------------------
// Получить текущую структуру JSON

document.getElementById('save-button').addEventListener('click', getFormData);

function getCurrentTime() {
    // Получаем текущее время в миллисекундах с начала эпохи
    const milliseconds = Date.now().toString().slice(0,11);
    return milliseconds;
}

function getFormData() {
    const form = document.getElementById('invoice-form');
    const data = {};
    const services = [];

    form.querySelectorAll('fieldset').forEach(fieldset => {
        const legend = fieldset.querySelector('legend');
        if (legend) {
            const fieldsetName = legend.textContent.trim();

            if (fieldset.classList.contains('service')) {
                const serviceData = {};
                fieldset.querySelectorAll('input, textarea, select').forEach(input => {
                    serviceData[input.name] = input.value;
                });
                services.push(serviceData);
            } else if (fieldsetName === 'Услуги') {
                data[fieldsetName] = services;
            } else {
                data[fieldsetName] = {};
                fieldset.querySelectorAll('input, textarea, select').forEach(input => {
                    data[fieldsetName][input.name] = input.value;
                });
            }
        }
    });

    form.querySelectorAll('input:not(fieldset input), textarea:not(fieldset textarea), select:not(fieldset select)').forEach(input => {
        if (!input.closest('fieldset')) {
            data[input.name] = input.value;
        }
    });

    // Сохранить JSON в файл
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;

    var currentTime = getCurrentTime();
    var originalFilename = document.getElementById('jsonfilenameid').getAttribute('jsonfilename');
    // 11 знаков (временная отметка)  + 1 "_" + 5 ".json" = 17 знаков
    var newFilename = originalFilename.slice(0, -17) + `_${currentTime}.json`;

    a.download = newFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}


// --------------------------------------------------------------------------------------------------------------------
// Подсветить ошибки

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('invoice-form');
    const keyNames = ['ИНН', 'КПП', 'БИК', 'корреспондентский счет', 'расчетный счет'];
    const regexes = [
        /^\d{10}$|^\d{12}$/, // inn
        /^\d{9}$/,           // kpp
        /^04\d{7}$/,         // bik
        /^30101\d{15}$/,     // ks
        /^(?:408|407|406|405)\d{17}$/ // rs
    ];

    const inputs = form.querySelectorAll('input');

    function validateInput(input) {
        const name = input.name;
        const index = keyNames.indexOf(name);
        if (index !== -1) {
            const regex = regexes[index];
            if (regex.test(input.value)) {
                input.classList.remove('error');
            } else {
                input.classList.add('error');
            }
        }
    }

    inputs.forEach(input => {
        input.addEventListener('input', () => validateInput(input));
        validateInput(input); // Initial validation
    });
});


// --------------------------------------------------------------------------------------------------------------------
// Список Услуг1С

document.addEventListener('DOMContentLoaded', dropdownService1C);

function dropdownService1C() {
    // Встроенные данные
    var originalJsonString = document.getElementById('services_dict').textContent;
    try {
        // Преобразуем строку JSON в объект JavaScript
        var data = JSON.parse(originalJsonString);
    } catch (error) {
        // В случае ошибки выводим сообщение об ошибке
        alert("Произошла ошибка: " + error.message);
        return;
    }

    const searchInputs = document.querySelectorAll('.Услуга1С');
    const dropdowns = document.querySelectorAll('.dropdown');
    let lastValidValue = '';

    searchInputs.forEach((element, index) => {
        const dropdown = dropdowns[index];
        element.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            dropdown.innerHTML = ''; // Очистка выпадающего списка
            if (query) {
                const filteredData = data.filter(item => item.comment.toLowerCase().includes(query));
                if (filteredData.length > 0) {
                    filteredData.forEach(item => {
                        const div = document.createElement('div');
                        div.classList.add('dropdown-item');
                        div.textContent = item.comment;
                        div.addEventListener('click', function() {
                            // Подсвечивание элемента зеленым цветом на 0.2 секунду
                            div.classList.add('highlight');
                            setTimeout(() => {
                                div.classList.remove('highlight');
                                element.value = item.comment;
                                lastValidValue = item.comment;
                                dropdown.innerHTML = '';
                                dropdown.style.display = 'none';
                            }, 150);
                        });
                        dropdown.appendChild(div);
                    });
                    dropdown.style.display = 'block';
                } else {
                    dropdown.style.display = 'none';
                }
            } else {
                dropdown.style.display = 'none';
            }
        });

        element.addEventListener('blur', function() {
            const value = this.value;
            const isValid = data.some(item => item.comment === value) || value === '';
            if (!isValid) {
                this.value = "";
            }
        });

        let isDragging = false;

        document.addEventListener('mousedown', function(event) {
            isDragging = false;
        });

        document.addEventListener('mousemove', function(event) {
            isDragging = true;
        });

        document.addEventListener('mouseup', function(event) {
            if (!isDragging && !element.contains(event.target) && !dropdown.contains(event.target)) {
                dropdown.style.display = 'none';
            }
            isDragging = false;
        });
    });
}
