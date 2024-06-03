document.addEventListener('DOMContentLoaded', function () {
    // Автоматическая настройка высоты textarea
    document.querySelectorAll('textarea').forEach(function(textarea) {
        textarea.style.height = textarea.scrollHeight + 'px';
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });

    const img = document.querySelector('.right-pane img');
    if (img) {
        let isZoomed = false;
        let isDragging = false;
        let startX, startY;

        img.addEventListener('mousedown', (e) => {
            if (isZoomed) {
                isDragging = true;
                startX = e.pageX - img.offsetLeft;
                startY = e.pageY - img.offsetTop;
                img.style.cursor = 'grabbing';
                e.preventDefault(); // Предотвращаем выделение текста
            }
        });

        img.addEventListener('mouseleave', () => {
            isDragging = false;
            img.style.cursor = isZoomed ? 'move' : 'grab';
        });

        img.addEventListener('mouseup', () => {
            isDragging = false;
            img.style.cursor = isZoomed ? 'move' : 'grab';
        });

        img.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const x = e.pageX - startX;
            const y = e.pageY - startY;
            img.style.left = `${x}px`;
            img.style.top = `${y}px`;
        });

        img.addEventListener('wheel', (e) => {
            if (e.ctrlKey) { // Только если зажата клавиша Ctrl
                if (e.deltaY > 0) {
                    // Zoom out
                    img.classList.remove('zoomed');
                    isZoomed = false;
                    img.style.cursor = 'grab';
                    img.style.position = 'absolute';
                    img.style.left = 'calc(50% - 50%)';
                    img.style.top = 'calc(50% - 50%)';
                } else {
                    // Zoom in
                    img.classList.add('zoomed');
                    isZoomed = true;
                    img.parentElement.style.overflow = 'scroll'; // Добавляем прокрутку при зумировании
                    img.style.cursor = 'move';
                    img.style.position = 'absolute';
                    img.style.left = '0';
                    img.style.top = '0';
                }
                e.preventDefault(); // Предотвращаем прокрутку страницы при зумировании
            }
        });
    }
	
	
});

document.getElementById('save-button').addEventListener('click', function() {
    const formData = [];
	
	const jsonFilename = document.getElementById('jsonfilenameid').getAttribute('jsonfilename');
	formData.push(jsonFilename);

    function collectFormData(element) {
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            if (element.type === 'checkbox') {
                formData.push(`${element.name}#${element.checked ? 'true' : 'false'}`);
            } else {
                formData.push(`${element.name}#${element.value}`);
            }
        } else if (element.tagName === 'FIELDSET') {
            const children = Array.from(element.children).filter(child => child.tagName !== 'LEGEND');
            children.forEach(child => collectFormData(child));
        }
    }

    const formElements = document.querySelectorAll('form input, form textarea, form fieldset');
    formElements.forEach(element => collectFormData(element));

    const textData = formData.join('\n');

    const blob = new Blob([textData], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'formData.txt';
    a.click();
    URL.revokeObjectURL(url);
});
