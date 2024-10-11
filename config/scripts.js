// --------------------------------------------------------------------------------------------------------------------
// Копирование выбранного варианта Номер сделки в буфер

document.addEventListener("DOMContentLoaded", function() {
    const selectElements = document.querySelectorAll('.Номерсделки');

    // Функция для копирования выбранного значения
    function copySelectedValue(selectElement) {
        const selectedValue = selectElement.options[selectElement.selectedIndex].text;

        // Создание временного текстового элемента для копирования
        const tempTextArea = document.createElement('textarea');
        tempTextArea.value = selectedValue;
        document.body.appendChild(tempTextArea);
        tempTextArea.select();
        document.execCommand('copy');
        document.body.removeChild(tempTextArea);

        console.log('Скопировано: ' + selectedValue);
    }

    // Применяем событие ко всем элементам с классом .Номерсделки
    selectElements.forEach(function(selectElement) {
        // Используем событие focus для копирования при фокусировке
        selectElement.addEventListener('focus', function() {
            copySelectedValue(selectElement);
        });

        // Копирование при изменении выбранного значения
        selectElement.addEventListener('change', function() {
            copySelectedValue(selectElement);
        });
    });
});


// --------------------------------------------------------------------------------------------------------------------
// Затемнение, блокировка полей цена/сумма сНДС/безНДС в зависимости от price_type

document.addEventListener('DOMContentLoaded', price_type_opacity);

function price_type_opacity() {
    // Function to update the opacity and disable status based on price type
    function updateOpacity(fieldset) {
        const priceTypeSelect = fieldset.querySelector('.price_type');
        const priceType = priceTypeSelect.value;
        const inputGroups = fieldset.querySelectorAll('.input-group');

        // Remove .opacity-50 and enable all inputs in the current fieldset
        inputGroups.forEach(group => {
            group.classList.remove('opacity-50');
            const input = group.querySelector('input');
            if (input) {
                input.removeAttribute('disabled'); // Снимаем отключение поля
            }
        });

        if (priceType === 'Сверху') {
            // Добавляем затемнение и отключаем соответствующие поля
            const priceWithVAT = fieldset.querySelector('.ЦенасНДС').parentElement;
            const sumWithVAT = fieldset.querySelector('.СуммасНДС').parentElement;

            priceWithVAT.classList.add('opacity-50');
            sumWithVAT.classList.add('opacity-50');

            priceWithVAT.querySelector('input').setAttribute('disabled', 'disabled');
            sumWithVAT.querySelector('input').setAttribute('disabled', 'disabled');
        } else {
            // Добавляем затемнение и отключаем соответствующие поля
            const priceWithoutVAT = fieldset.querySelector('.ЦенабезНДС').parentElement;
            const sumWithoutVAT = fieldset.querySelector('.СуммабезНДС').parentElement;

            priceWithoutVAT.classList.add('opacity-50');
            sumWithoutVAT.classList.add('opacity-50');

            priceWithoutVAT.querySelector('input').setAttribute('disabled', 'disabled');
            sumWithoutVAT.querySelector('input').setAttribute('disabled', 'disabled');
        }
    }

    // Select all fieldsets containing the service blocks
    const fieldsets = document.querySelectorAll('fieldset.service');

    // Iterate over each fieldset and add event listeners to its select element
    fieldsets.forEach(fieldset => {
        const priceTypeSelect = fieldset.querySelector('.price_type');

        // Add event listener for when the select changes
        priceTypeSelect.addEventListener('change', function() {
            updateOpacity(fieldset);
        });

        // Run the function once on page load for each fieldset
        updateOpacity(fieldset);
    });
}


// --------------------------------------------------------------------------------------------------------------------
// Очистка одного из полей класса .Услуга1С - .Услуга1Сновая

document.addEventListener('DOMContentLoaded', good_input_cleaner);

function good_input_cleaner() {
    // Получаем все fieldset с классом 'service'
    const fieldsets = document.querySelectorAll('fieldset.service');

    fieldsets.forEach(fieldset => {
        // Находим соответствующие пары textarea в каждом fieldset
        const good1C = fieldset.querySelector('.Услуга1С');
        const good1CNew = fieldset.querySelector('.Услуга1Сновая');

        // Функция для очистки good1C, если в good1CNew есть текст
        function handleInput2() {
            if (good1CNew.value.trim() !== '') {
                good1C.value = '';
            }
        }

        // Функция для очистки good1CNew, если в good1C есть текст
        function handleInput1() {
            if (good1C.value.trim() !== '') {
                good1CNew.value = '';
            }
        }

        // Добавляем слушатели событий на textarea
        if (good1C && good1CNew) {
            good1CNew.addEventListener('input', handleInput2);
            good1C.addEventListener('input', handleInput1);
            good1CNew.addEventListener('change', handleInput2);
            good1C.addEventListener('change', handleInput1);
        }
    });
}


// --------------------------------------------------------------------------------------------------------------------
// Очистка одного из полей класса .Номерсделки / .Номерсделкиввестисвой

document.addEventListener('DOMContentLoaded', sdelka_cleaner);

function sdelka_cleaner() {

    // Находим все поля с классом .Номерсделки / .Номерсделкиввестисвой
    const sdelkaElements = document.querySelectorAll('.Номерсделки');
    const sdelkaNewElements = document.querySelectorAll('.Номерсделкиввестисвой');

    // Проверяем, чтобы количество элементов в обоих коллекциях было одинаковым
    if (sdelkaElements.length !== sdelkaNewElements.length) {
        console.error('Количество элементов с классами .Номерсделки и .Номерсделкиввестисвой не совпадает.');
        return;
    }

    // Функция для обработки каждого набора полей
    sdelkaElements.forEach((sdelka, index) => {
        const sdelka_new = sdelkaNewElements[index];

        // Функция для очистки .Номерсделки, если в .Номерсделкиввестисвой есть текст
        function handleInput2() {
            if (sdelka_new.value.trim() !== '') {
                sdelka.value = 'Нет';
            }
        }

        // Функция для очистки .Номерсделкиввестисвой, если в .Номерсделки есть текст
        function handleInput1() {
            if (sdelka.value.trim() !== 'Нет') {
                sdelka_new.value = '';
            }
        }

        // Добавляем слушатели событий на каждую пару элементов
        if (sdelka && sdelka_new) {
            sdelka_new.addEventListener('input', handleInput2);
            sdelka.addEventListener('input', handleInput1);
            sdelka_new.addEventListener('change', handleInput2);
            sdelka.addEventListener('change', handleInput1);
        }
    });
}


// --------------------------------------------------------------------------------------------------------------------
// Размер textarea

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
}

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация начального размера для всех текстовых полей
    document.querySelectorAll('textarea').forEach(textarea => {
        autoResize(textarea);
    });
});


// --------------------------------------------------------------------------------------------------------------------
// zoom jpg в правой части страницы

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
    // Вызов good_input_cleaner после добавления нового service для обновления элементов класса Услуга1С, Услуга1Сновая
    good_input_cleaner();
    // Вызов price_type_opacity после добавления нового service для обновления элементов .price_type
    price_type_opacity();
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
    const keyNames = ['ИНН', 'КПП', 'БИК', 'корреспондентский счет', 'расчетный счет', 'nds (%)'];
    const regexes = [
        /^\d{10}$|^\d{12}$/, // inn
        /^\d{9}$/,           // kpp
        /^04\d{7}$/,         // bik
        /^30101\d{15}$/,     // ks
        /^(?:408|407|406|405)\d{17}$/, // rs
        /^(20|20\.0+|0|0\.0+)$/ // nds
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
    var originalJsonString = document.getElementById('unique_services').textContent;
    try {
        // Преобразуем строку JSON в объект JavaScript (список строк)
        var data = JSON.parse(originalJsonString);
    } catch (error) {
        // В случае ошибки выводим сообщение об ошибке
        console.log("Произошла ошибка: " + error.message);
        return;
    }

    // Поскольку в services_dict уже хранятся уникальные значения, можно сразу использовать data
    const uniqueServices = data;  // services_dict уже содержит уникальные значения

    const searchInputs = document.querySelectorAll('.Услуга1С');
    const dropdowns = document.querySelectorAll('.dropdown');
    let lastValidValue = '';

    searchInputs.forEach((element, index) => {
        autoResize(element);
        const dropdown = dropdowns[index];
        element.addEventListener('input', function() {
            autoResize(this);
            const query = this.value.toLowerCase();
            dropdown.innerHTML = ''; // Очистка выпадающего списка
            if (query) {
                const filteredData = uniqueServices.filter(service => service.toLowerCase().includes(query));
                if (filteredData.length > 0) {
                    filteredData.forEach(service => {
                        const div = document.createElement('div');
                        div.classList.add('dropdown-item');
                        div.textContent = service;
                        div.addEventListener('click', function() {
                            // Подсвечивание элемента зеленым цветом на 0.2 секунду
                            div.classList.add('highlight');
                            setTimeout(() => {
                                div.classList.remove('highlight');
                                element.value = service;
                                lastValidValue = service;
                                dropdown.innerHTML = '';
                                dropdown.style.display = 'none';
                                autoResize(element);

                                // Вызов события change вручную
                                const event = new Event('change');
                                element.dispatchEvent(event);

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
            const isValid = uniqueServices.includes(value) || value === '';
            if (!isValid) {
                this.value = "";
                autoResize(this);
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