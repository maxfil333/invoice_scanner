// Функция для перерасчета цен и сумм от количества/НДС/цен
function recalculate() {
    const autoRecalculateCheckbox = document.querySelector('.switch input[type="checkbox"]');
    if (autoRecalculateCheckbox.checked) {
        document.querySelectorAll('.service').forEach(service => {
            let priceType = service.querySelector('.price_type').value;
            let nds = parseFloat(service.querySelector('.nds').value) || 0;
            let priceWithoutNDS = parseFloat(service.querySelector('.ЦенабезНДС').value) || 0;
            let priceWithNDS = parseFloat(service.querySelector('.ЦенасНДС').value) || 0;
            let quantity = parseFloat(service.querySelector('.Количество').value) || 1;

            // Логика перерасчета цены в зависимости от price_type
            if (priceType === "Сверху") {
                // СуммаБез = Кол-во * ЦенаБеЗ
                let sumWithoutNDS = quantity * priceWithoutNDS;
                service.querySelector('.СуммабезНДС').value = sumWithoutNDS.toFixed(2);

                // ЦенаС = ЦенаБез * (1 + nds /100)
                priceWithNDS = priceWithoutNDS * (1 + nds / 100);
                service.querySelector('.ЦенасНДС').value = priceWithNDS.toFixed(2);

                // СуммаС = Кол-во * ЦенаС
                sumWithNDS = quantity * priceWithNDS;
                service.querySelector('.СуммасНДС').value = sumWithNDS.toFixed(2);

                // Просто округление до двух знаков
                service.querySelector('.ЦенабезНДС').value = priceWithoutNDS.toFixed(2);

            } else if (priceType === "В т.ч.") {
                // СуммаС = Кол-во * ЦенаС
                let sumWithNDS = quantity * priceWithNDS;
                service.querySelector('.СуммасНДС').value = sumWithNDS.toFixed(2);

                // ЦенаБез = ЦенаС * 100 / (100 + nds)
                priceWithoutNDS = priceWithNDS * 100 / (100 + nds);
                service.querySelector('.ЦенабезНДС').value = priceWithoutNDS.toFixed(2);

                // СуммаБез = Кол-во * ЦенаБез
                sumWithoutNDS = quantity * priceWithoutNDS;
                service.querySelector('.СуммабезНДС').value = sumWithoutNDS.toFixed(2);

                // Просто округление до двух знаков
                service.querySelector('.ЦенасНДС').value = priceWithNDS.toFixed(2);
            }
        });
    }
}

// Функция для инициализации событий на указанных полях
function initListeners_recalculate() {
    const fieldsToWatch = ['.nds', '.price_type', '.ЦенасНДС', '.ЦенабезНДС', '.Количество'];

    // Добавление обработчика событий для указанных полей
    fieldsToWatch.forEach(selector => {
        document.querySelectorAll(selector).forEach(input => {
            input.addEventListener('input', recalculate);
        });
    });

    // Обработчик события изменения состояния чекбокса
    const autoRecalculateCheckbox = document.querySelector('.switch input[type="checkbox"]');
    if (autoRecalculateCheckbox) {
        autoRecalculateCheckbox.addEventListener('change', () => {
            if (autoRecalculateCheckbox.checked) {
                recalculate(); // Вызываем пересчет при изменении состояния на checked
            }
        });
    }
}

// Запуск функции при загрузке страницы
window.addEventListener('load', function() {
    initListeners_recalculate();
    recalculate(); // начальный расчет
});


// --------------------------------------------------------------------------------------------------------------------
// Функция для перерасчета цены на основе суммы
function recalculate_price_by_sum() {
    const autoRecalculateCheckbox = document.querySelector('.switch input[type="checkbox"]');
    if (autoRecalculateCheckbox.checked) {
        document.querySelectorAll('.service').forEach(service => {
            let priceType = service.querySelector('.price_type').value;
            let nds = parseFloat(service.querySelector('.nds').value) || 0;
            let quantity = parseFloat(service.querySelector('.Количество').value) || 1;
            let sumWithoutNDS = parseFloat(service.querySelector('.СуммабезНДС').value) || 0;
            let sumWithNDS = parseFloat(service.querySelector('.СуммасНДС').value) || 0;

            // Рассчитываем цены на основании суммы и количества
            let priceWithoutNDS = sumWithoutNDS / quantity;
            service.querySelector('.ЦенабезНДС').value = priceWithoutNDS.toFixed(2);
            let priceWithNDS = sumWithNDS / quantity;
            service.querySelector('.ЦенасНДС').value = priceWithNDS.toFixed(2);

            // Логика перерасчета цены в зависимости от priceType
            if (priceType === "Сверху") {
                priceWithNDS = priceWithoutNDS * (1 + nds / 100);
                service.querySelector('.ЦенасНДС').value = priceWithNDS.toFixed(2);

                sumWithNDS = priceWithNDS * quantity;
                service.querySelector('.СуммасНДС').value = sumWithNDS.toFixed(2);
            } else if (priceType === "В т.ч.") {
                priceWithoutNDS = priceWithNDS * 100 / (100 + nds);
                service.querySelector('.ЦенабезНДС').value = priceWithoutNDS.toFixed(2);

                sumWithoutNDS = priceWithoutNDS * quantity
                service.querySelector('.СуммабезНДС').value = sumWithoutNDS.toFixed(2);
            }
        });
    }
}

// Функция для инициализации событий на полях "Сумма без НДС" и "Сумма с НДС"
function initListeners_recalculate_price_by_sum() {
    const fieldsToWatch = ['.СуммабезНДС', '.СуммасНДС'];

    fieldsToWatch.forEach(selector => {
        document.querySelectorAll(selector).forEach(input => {
            input.addEventListener('input', recalculate_price_by_sum);
        });
    });
}

// Запуск слушателей при загрузке страницы
window.addEventListener('load', function() {
    initListeners_recalculate_price_by_sum();
});


// --------------------------------------------------------------------------------------------------------------------
// Функция для проверки соответствия сумм всех услуг значениям "ВсегокоплатевключаяНДС" и "ВсегоНДС"
function validate_total_amount() {
    let totalSumWithNDS = 0;
    let totalNDSDifference = 0;

    // Суммируем все значения "СуммасНДС" и разницу между "СуммасНДС" и "СуммабезНДС" из всех услуг
    document.querySelectorAll('.service').forEach(service => {
        let sumWithNDS = parseFloat(service.querySelector('.СуммасНДС').value) || 0;
        let sumWithoutNDS = parseFloat(service.querySelector('.СуммабезНДС').value) || 0;

        totalSumWithNDS += sumWithNDS;
        totalNDSDifference += (sumWithNDS - sumWithoutNDS);
    });

    // Заполнение поверочных полей #last
    document.querySelector('#last_total_with').value = `Σ(по услугам): ${totalSumWithNDS.toFixed(2) || 0}`;
    document.querySelector('#last_total_nds').value = `Σ(по услугам): ${totalNDSDifference.toFixed(2) || 0}`;

    // Проверка "ВсегокоплатевключаяНДС"
    let totalAmountField = document.querySelector('.ВсегокоплатевключаяНДС');
    let totalAmountValue = parseFloat(totalAmountField.value) || 0;
    console.log('ВсегокоплатевключаяНДС:', 'sum:', totalSumWithNDS.toFixed(2), 'total:', totalAmountValue.toFixed(2))

    if (totalSumWithNDS.toFixed(2) === totalAmountValue.toFixed(2)) {
        totalAmountField.style.backgroundColor = '#A5F0B0';
    } else {
        totalAmountField.style.backgroundColor = '#f2dce0';
    }

    // Проверка "ВсегоНДС"
    let totalNDSField = document.querySelector('.ВсегоНДС');
    let totalNDSValue = parseFloat(totalNDSField.value) || 0;
    console.log('ВсегоНДС:', 'sum:', totalNDSDifference.toFixed(2), 'total:', totalNDSValue.toFixed(2))

    if (totalNDSDifference.toFixed(2) === totalNDSValue.toFixed(2)) {
        totalNDSField.style.backgroundColor = '#A5F0B0';
    } else {
        totalNDSField.style.backgroundColor = '#f2dce0';
    }
}

// Функция для инициализации проверки при изменении полей
function initListeners_validate_total_amount() {
    const fieldsToWatch = ['.СуммабезНДС', '.СуммасНДС', '.nds', '.price_type',
        '.ЦенасНДС', '.ЦенабезНДС', '.Количество', '.ВсегокоплатевключаяНДС', '.ВсегоНДС'];

    // Добавление обработчика событий для указанных полей
    fieldsToWatch.forEach(selector => {
        document.querySelectorAll(selector).forEach(input => {
            input.addEventListener('input', validate_total_amount);
        });
    });

    // Добавление обработчика для всех чекбоксов
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', validate_total_amount);
    });
}

// Запуск проверки и инициализации событий при загрузке страницы
window.addEventListener('load', function() {
    initListeners_validate_total_amount();
    validate_total_amount(); // начальная проверка при загрузке
});


// --------------------------------------------------------------------------------------------------------------------
// Затемнение, блокировка полей цена/сумма сНДС/безНДС в зависимости от price_type

document.addEventListener('DOMContentLoaded', price_type_opacity);

function price_type_opacity() {
    // Function to update the opacity and disable status based on price type
    function updateOpacity(fieldset) {
        const autoRecalculateCheckbox = document.querySelector('.switch input[type="checkbox"]');
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

             if (autoRecalculateCheckbox.checked) {
                priceWithVAT.querySelector('input').setAttribute('disabled', 'disabled');
                sumWithVAT.querySelector('input').setAttribute('disabled', 'disabled');
                }
        } else {
            // Добавляем затемнение и отключаем соответствующие поля
            const priceWithoutVAT = fieldset.querySelector('.ЦенабезНДС').parentElement;
            const sumWithoutVAT = fieldset.querySelector('.СуммабезНДС').parentElement;

            priceWithoutVAT.classList.add('opacity-50');
            sumWithoutVAT.classList.add('opacity-50');

            if (autoRecalculateCheckbox.checked) {
                priceWithoutVAT.querySelector('input').setAttribute('disabled', 'disabled');
                sumWithoutVAT.querySelector('input').setAttribute('disabled', 'disabled');
                }
        }
    }

    // Select all fieldsets containing the service blocks
    const fieldsets = document.querySelectorAll('fieldset.service');

    // Iterate over each fieldset and add event listeners to its select element
    fieldsets.forEach(fieldset => {
        const priceTypeSelect = fieldset.querySelector('.price_type');
        const autoRecalculateCheckbox = document.querySelector('.switch input[type="checkbox"]');

        // Add event listener для смены price_type и для смены autoRecalculateCheckbox
        [priceTypeSelect, autoRecalculateCheckbox].forEach(element => {
            element.addEventListener('change', function() {
                updateOpacity(fieldset);
            });
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
// Добавить новую услугу

function addService(button) {
    var fieldset = button.parentElement;
    var services = fieldset.querySelectorAll('fieldset');

    if (services.length === 0) return;

    var firstService = services[0];
    var newService = firstService.cloneNode(true);

    var number_of_deal = newService.querySelector('.Номерсделки');
    number_of_deal.removeAttribute("style");
    number_of_deal.className = "Номерсделки"; // если был зеленый стиль, убираем

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

    // Вызов очистки сделок (для того чтобы найти новое поле "Номер сделки")
    sdelka_cleaner();
    // Вызов копирования сделки в буфер (для того чтобы найти новое поле "Номер сделки")
    copyToBufferService1C();
    // Вызов функции dropdownService1C после добавления нового service
    dropdownService1C();
    // Вызов good_input_cleaner после добавления нового service для обновления элементов класса Услуга1С, Услуга1Сновая
    good_input_cleaner();
    // Вызов price_type_opacity после добавления нового service для обновления элементов .price_type
    price_type_opacity();
    // Вызов подсветки ошибок после добавления нового service
    highlight_errors();
    // Вызов перерасчета значений цен, сумм от количества/НДС/цен
    initListeners_recalculate();
    recalculate();
    // Вызов перерасчета значений цены от суммы
    initListeners_recalculate_price_by_sum();
    recalculate_price_by_sum();
    // Проверка соответствия суммы "СуммасНДС" всех услуг значению "ВсегокоплатевключаяНДС"
    initListeners_validate_total_amount();
    validate_total_amount();
    // замена запятой на точку
    replaceCommaWithDot();
}


// --------------------------------------------------------------------------------------------------------removeService
// Удалить услугу

function removeService() {
    let inputValue = prompt("Укажите номера услуг для удаления (через пробел)");
    if (inputValue !== null) {
        let numbersToDelete = inputValue
            .split(" ")
            .map(num => num.trim())
            .filter(num => num !== "");

        // Преобразуем в набор уникальных номеров и обратно в массив
        let uniqueNumbersToDelete = [...new Set(numbersToDelete)];

        // Получаем список всех услуг
        let fieldsets = Array.from(document.querySelectorAll("fieldset.service"));


        // Ищем, какие из указанных номеров отсутствуют
        let missingNumbers = uniqueNumbersToDelete.filter(number => {
            return !fieldsets.some(fieldset => {
                let legend = fieldset.querySelector("legend");
                return legend && legend.textContent.trim() === number;
            });
        });

        // Если хоть один номер не найден – показываем сообщение и прерываем выполнение
        if (missingNumbers.length > 0) {
            alert("Услуги с указанными номерами не найдены: " + missingNumbers.join(", "));
            return;
        }

        // Проверяем, чтобы после удаления осталось хотя бы одна услуга
        if (fieldsets.length - uniqueNumbersToDelete.length < 1) {
            alert("Нельзя удалить единственную услугу.");
            return;
        }

        // Если все услуги найдены – удаляем их
        fieldsets.forEach(fieldset => {
            let legend = fieldset.querySelector("legend");
            if (legend && uniqueNumbersToDelete.includes(legend.textContent.trim())) {
                fieldset.remove();
            }
        });
    }

    // Вызов перерасчета значений цен, сумм от количества/НДС/цен
    initListeners_recalculate();
    recalculate();
    // Вызов перерасчета значений цены от суммы
    initListeners_recalculate_price_by_sum();
    recalculate_price_by_sum();
    // Проверка соответствия суммы "СуммасНДС" всех услуг значению "ВсегокоплатевключаяНДС"
    initListeners_validate_total_amount();
    validate_total_amount();
}


// --------------------------------------------------------------------------------------------------------------------
// Подсветить ошибки
document.addEventListener('DOMContentLoaded', highlight_errors);

function highlight_errors() {
    const form = document.getElementById('invoice-form');
    const keyNames = ['ИНН', 'КПП', 'БИК', 'корреспондентский счет', 'расчетный счет', 'nds (%)'];
    const regexes = [
        /^\d{10}$|^\d{12}$/, // inn
        /^\d{9}$/,           // kpp
        /^04\d{7}$/,         // bik
        /^30101\d{15}$/,     // ks
        /^(?:408|407|406|405)\d{17}$/, // rs
        /^(20|20\.0+|0|0\.0+|без ндс)$/i // nds
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
}


// Подсветить локальные поля в которых есть нераспознанные сущности
document.addEventListener('DOMContentLoaded', processDealsAndHighlightErrors);

function processDealsAndHighlightErrors() {
    // Получить содержимое элемента класса "Ненайденныесделки"
    const not_found_extra_field = document.querySelector('.Ненайденныесделки');
    if (!not_found_extra_field) return; // Если элемент не найден, ничего не делаем
    if (!not_found_extra_field.textContent.trim()) return; // Если элемент пустой, ничего не делаем

    // Разбить содержимое на список по разделителю переноса строки
    const ents = not_found_extra_field.textContent.split('\n');

    // Пройти по всем элементам input класса service
    const serviceInputs = document.querySelectorAll('.service input, .service textarea');

    serviceInputs.forEach(input => {
        if (ents.includes(input.value)) {
            input.classList.add('error'); // Добавить класс error
        }
    });
}

// Подсветить additional_data.Нераспознанные_сделки
document.addEventListener('DOMContentLoaded', HighlightNotFoundExtraField);

function HighlightNotFoundExtraField() {
    const not_found_extra_field = document.querySelector('.Ненайденныесделки');
    if (not_found_extra_field.value.trim() !== "") {
        not_found_extra_field.classList.add('error');
    }
}


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


// --------------------------------------------------------------------------------------------------------------------
// Получить текущую структуру JSON

document.getElementById('save-button').addEventListener('click', getFormData);

function getCurrentTime() {
    // Получаем текущее время в миллисекундах с начала эпохи
    const milliseconds = Date.now().toString().slice(0,11);
    return milliseconds;
}

function getFormData() {
    // Находим форму с id 'invoice-form'
    const form = document.getElementById('invoice-form');
    // Создаем пустой объект для хранения данных формы
    const data = {};
    // Массив для хранения данных полей, относящихся к услугам
    const services = [];

    // Проходим по всем fieldset (группам полей) формы
    form.querySelectorAll('fieldset').forEach(fieldset => {
        // Ищем элемент legend (заголовок fieldset) и сохраняем его текст
        const legend = fieldset.querySelector('legend');
        if (legend) {
            // Получаем имя fieldset из текста legend и удаляем лишние пробелы
            const fieldsetName = legend.textContent.trim();

            // Проверяем, если fieldset имеет класс 'service'
            if (fieldset.classList.contains('service')) {
                // Создаем объект для хранения данных конкретной услуги
                const serviceData = {};

                // Собираем все input, textarea и select в этом fieldset
                fieldset.querySelectorAll('input, textarea, select').forEach(input => {
                    // Добавляем данные поля в объект serviceData по имени поля (input.name)
                    serviceData[input.name] = input.value;
                });

                // Добавляем объект serviceData в массив services
                services.push(serviceData);

            // Проверяем, если это fieldset с названием 'Услуги'
            } else if (fieldsetName === 'Услуги') {
                // Записываем массив услуг в общий объект data под ключом 'Услуги'
                data[fieldsetName] = services;
            } else {
                // Если это другой fieldset, создаем для него пустой объект в data
                data[fieldsetName] = {};

                // Собираем все input, textarea и select в этом fieldset
                fieldset.querySelectorAll('input, textarea, select').forEach(input => {
                    // Добавляем данные в объект по имени поля input.name
                    data[fieldsetName][input.name] = input.value;
                });
            }
        }
    });

    // Собираем все input, textarea, select, которые не находятся внутри fieldset и не имеют класс "not_for_json"
    form.querySelectorAll('input:not(fieldset input):not(.not_for_json), textarea:not(fieldset textarea):not(.not_for_json), select:not(fieldset select):not(.not_for_json)').forEach(input => {
        // Если элемент не находится внутри fieldset
        if (!input.closest('fieldset')) {
            // Добавляем его в общий объект data, если он не имеет класс "not_for_json"
            data[input.name] = input.value;
        }
    });

    // contract (contract_details Договор)
    const selectDisplay = form.querySelector('#contract-selector');
    if (selectDisplay) {
        data['contract_details']['Договор'] = selectDisplay.textContent.trim();
    }

    // Сохранить JSON в файл
    const json = JSON.stringify(data, null, 4);
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
// Копирование выбранного варианта Номер сделки в буфер

document.addEventListener('DOMContentLoaded', copyToBufferService1C);

function copyToBufferService1C() {
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
}


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
// Подсветить сделку зеленым если сделка всего одна

document.addEventListener('DOMContentLoaded', highlight_one_service);

function highlight_one_service() {
    // Ищем все элементы с классом Номерсделки
    const selectElements = document.querySelectorAll('.Номерсделки');

    selectElements.forEach(select => {
        // Проверяем условие для green-background
        if (select.options.length === 2) {
            select.classList.add('green-background');
        } else {
            // Фильтруем элементы, исключая те, которые начинаются с "ТБ" или равны "Нет"
            const filteredOptions = Array.from(select.options).filter(option => {
                return !option.text.startsWith('ТБ') && option.text !== 'Нет';
            });

            // Проверяем условие для lightgreen-background
            if (filteredOptions.length === 1) {
                select.classList.add('lightgreen-background');
            }
        }
    });
}


// ------------------------------------------------------------------------------------------------------------ CONTRACT

document.addEventListener("DOMContentLoaded", function () {
    const customSelect = document.querySelector("#contract-custom");
    const selectDisplay = customSelect.querySelector("#contract-selector");
    const options = customSelect.querySelector(".options");
    const contractId = document.querySelector('.ДоговорИдентификатор');

    selectDisplay.addEventListener("click", function (event) {
        event.stopPropagation(); // Останавливаем всплытие
        customSelect.classList.toggle("open");
    });

    options.addEventListener("mousedown", function (event) {
        // Проверяем, кликнули ли по дочернему элементу внутри .options
        if (event.target && event.target.parentElement === options) {
            event.preventDefault(); // Предотвращаем выделение текста
            selectDisplay.textContent = event.target.textContent; // Обновляем текст
            contractId.textContent = contract_get_id(event.target.textContent); // Получаем ID
            customSelect.classList.remove("open");
        }
    });

    document.addEventListener("click", function () {
        customSelect.classList.remove("open");
    });
});

function contract_get_id(contract) {
    const variants = JSON.parse(document.querySelector('.Варианты').textContent);
    for (let variant of variants) {
        if (variant['Договор'].trim() === contract.trim()) {
            return variant['ДоговорИдентификатор'];
        }
    }
    return null;
}

// --------------------------------------------------------------------------------------------------------------------
// Замена запятой на точку в числовых полях

document.addEventListener('DOMContentLoaded', replaceCommaWithDot);

function replaceCommaWithDot() {
    const fieldsToWatch = ['.Количество', '.ЦенабезНДС', '.СуммабезНДС', '.ЦенасНДС', '.СуммасНДС'];

    fieldsToWatch.forEach(selector => {
        document.querySelectorAll(selector).forEach(input => {
            input.addEventListener('input', function() {
                this.value = this.value.replace(',', '.');
            });
            input.addEventListener('blur', function() {
                this.value = isNaN(Number(this.value)) ? '' : this.value;
            });
        });
    });
}

// ---------------------------------------------------------------------------------------------------------------"Даты"
// Проверка формата значения поля "Даты"

document.addEventListener('DOMContentLoaded', clearInvalidDates);

function clearInvalidDates() {
    const dateFields = document.querySelectorAll('.Даты');
    const dateRegex = /^\d{2}\.\d{2}\.\d{4} \d{2}\.\d{2}\.\d{4}$/; // Регулярное выражение

    dateFields.forEach(field => {
        if (field.value !== "" && !dateRegex.test(field.value)) {
            field.value = "";
        }
    });
}

document.addEventListener('blur', (event) => {
    if (event.target.classList.contains('Даты')) {
        const dateRegex = /^\d{2}\.\d{2}\.\d{4} \d{2}\.\d{2}\.\d{4}$/;
        if (event.target.value !== "" && !dateRegex.test(event.target.value)) {
            event.target.value = "";
        }
    }
}, true); // Используем `true`, чтобы событие срабатывало на всплытие (capture)
