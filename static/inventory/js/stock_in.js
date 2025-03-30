document.addEventListener('DOMContentLoaded', function() {
    const imageContainer = document.getElementById('image-container');
    const imageUpload = document.getElementById('image-upload');
    const productImage = document.getElementById('product-image');
    const imagePlaceholder = document.getElementById('image-placeholder');
    const loadingIndicator = document.querySelector('.loading-indicator');
    
    const productIdField = document.getElementById('product-id');
    const productCodeField = document.getElementById('product-code');
    const productNameField = document.getElementById('product-name');
    const categoryNameField = document.getElementById('category-name');
    const storeSelect = document.getElementById('store');
    const costPriceField = document.getElementById('cost-price');
    const quantityField = document.getElementById('quantity');
    const receiptDateField = document.getElementById('receipt-date');
    const totalPriceField = document.getElementById('total-price');
    const noteField = document.getElementById('note');
    
    const saveBtn = document.getElementById('save-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    
    // 이미지 컨테이너 클릭 이벤트
    imageContainer.addEventListener('click', function() {
        imageUpload.click();
    });
    
    // 이미지 업로드 이벤트
    imageUpload.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            
            // FormData 객체 생성
            const formData = new FormData();
            formData.append('image', file);
            
            // 로딩 표시
            imagePlaceholder.classList.add('d-none');
            loadingIndicator.classList.remove('d-none');
            
            // 이미지 업로드 API 호출
            fetch('/inventory/api/upload-image/', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loadingIndicator.classList.add('d-none');
                
                if (data.success) {
                    // 이미지 표시
                    productImage.src = data.image_url;
                    productImage.classList.remove('d-none');
                    
                    // 상품 정보 표시
                    productIdField.value = data.product_id;
                    productCodeField.value = data.product_code;
                    productNameField.value = data.product_name;
                    categoryNameField.value = data.category || '';
                    costPriceField.value = data.last_cost_price;
                    
                    // 매장 옵션 설정 (사용자가 선택한 매장이 있으면 유지)
                    if (data.stores.length === 1) {
                        const storeId = data.stores[0].id;
                        for (let i = 0; i < storeSelect.options.length; i++) {
                            if (storeSelect.options[i].value == storeId) {
                                storeSelect.selectedIndex = i;
                                break;
                            }
                        }
                    }
                    
                    // 폼 활성화
                    saveBtn.disabled = false;
                    calculateTotal();
                } else {
                    // 오류 처리
                    alert(data.message);
                    imagePlaceholder.classList.remove('d-none');
                }
            })
            .catch(error => {
                loadingIndicator.classList.add('d-none');
                imagePlaceholder.classList.remove('d-none');
                console.error('Error:', error);
                alert('이미지 업로드 중 오류가 발생했습니다.');
            });
        }
    });
    
    // 입고 단가 및 수량 변경 이벤트
    costPriceField.addEventListener('input', calculateTotal);
    quantityField.addEventListener('input', calculateTotal);
    
    // 합계 계산 함수
    function calculateTotal() {
        const costPrice = parseFloat(costPriceField.value) || 0;
        const quantity = parseInt(quantityField.value) || 0;
        const total = costPrice * quantity;
        totalPriceField.value = total.toFixed(2);
    }
    
    // 저장 버튼 클릭 이벤트
    saveBtn.addEventListener('click', function() {
        const productId = productIdField.value;
        const storeId = storeSelect.value;
        const costPrice = parseFloat(costPriceField.value);
        const quantity = parseInt(quantityField.value);
        const receiptDate = receiptDateField.value;
        const note = noteField.value;
        
        if (!productId || !storeId || isNaN(costPrice) || isNaN(quantity) || costPrice <= 0 || quantity <= 0) {
            alert('모든 필드를 올바르게 입력해주세요.');
            return;
        }
        
        const data = {
            product_id: productId,
            store_id: storeId,
            cost_price: costPrice,
            quantity: quantity,
            receipt_date: receiptDate,
            note: note
        };
        
        // 입고 정보 저장 API 호출
        fetch('/inventory/api/save-stock-in/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                resetForm();
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('입고 정보 저장 중 오류가 발생했습니다.');
        });
    });
    
    // 취소 버튼 클릭 이벤트
    cancelBtn.addEventListener('click', resetForm);
    
    // 폼 초기화 함수
    function resetForm() {
        productImage.classList.add('d-none');
        imagePlaceholder.classList.remove('d-none');
        
        productIdField.value = '';
        productCodeField.value = '';
        productNameField.value = '';
        categoryNameField.value = '';
        costPriceField.value = '';
        quantityField.value = '1';
        receiptDateField.value = new Date().toISOString().split('T')[0];
        totalPriceField.value = '';
        noteField.value = '';
        
        saveBtn.disabled = true;
        imageUpload.value = '';
    }
    
    // CSRF 토큰 가져오기 함수
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});