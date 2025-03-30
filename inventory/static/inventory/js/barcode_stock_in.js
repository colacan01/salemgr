document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소 참조
    const barcodeInput = document.getElementById('barcode-input');
    const searchBtn = document.getElementById('search-btn');
    const receiptTable = document.getElementById('receipt-table');
    const tableBody = receiptTable.querySelector('tbody');
    const emptyMessage = document.getElementById('empty-message');
    const totalAmountEl = document.getElementById('total-amount');
    const receiptDateInput = document.getElementById('receipt-date');
    const saveAllBtn = document.getElementById('save-all-btn');
    
    // 상품 목록 관리
    let receiptItems = [];
    
    // 바코드 입력란 엔터 이벤트
    barcodeInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            searchProduct();
        }
    });
    
    // 검색 버튼 클릭 이벤트
    searchBtn.addEventListener('click', searchProduct);
    
    // 저장 버튼 클릭 이벤트
    saveAllBtn.addEventListener('click', saveAllReceipts);
    
    // 바코드로 상품 검색 함수
    function searchProduct() {
        const barcode = barcodeInput.value.trim();
        if (!barcode) {
            alert('바코드를 입력해주세요.');
            return;
        }
        
        // 로딩 표시 추가
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 검색 중...';
        
        // API 호출
        fetch(`/inventory/api/search-product-by-barcode/?barcode=${barcode}`)
            .then(response => response.json())
            .then(data => {
                // 로딩 표시 제거
                searchBtn.disabled = false;
                searchBtn.innerHTML = '검색';
                
                if (data.success) {
                    // 이미 목록에 있는지 확인
                    const existingIndex = receiptItems.findIndex(item => item.product_id === data.product.id);
                    
                    if (existingIndex !== -1) {
                        // 이미 있으면 수량만 증가
                        receiptItems[existingIndex].quantity += 1;
                        updateTableRow(existingIndex);
                    } else {
                        // 새 상품이면 추가
                        const newItem = {
                            product_id: data.product.id,
                            product_code: data.product.code,
                            product_name: data.product.name,
                            store_id: data.product.store_id || getDefaultStoreId(),
                            cost_price: data.product.last_cost_price || 0,
                            quantity: 1,
                            note: '',
                            product_detail: data.product
                        };
                        
                        receiptItems.push(newItem);
                        addTableRow(receiptItems.length - 1);
                    }
                    
                    // 입력란 초기화 및 포커스
                    barcodeInput.value = '';
                    barcodeInput.focus();
                    
                    // 총액 업데이트
                    updateTotalAmount();
                    
                    // 저장 버튼 활성화
                    saveAllBtn.disabled = false;
                    
                    // 빈 메시지 숨기기
                    emptyMessage.style.display = 'none';
                } else {
                    alert(data.message);
                    barcodeInput.select();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('상품 검색 중 오류가 발생했습니다.');
                searchBtn.disabled = false;
                searchBtn.innerHTML = '검색';
            });
    }
    
    // 테이블에 행 추가
    function addTableRow(index) {
        const item = receiptItems[index];
        const row = document.createElement('tr');
        row.dataset.index = index;
        
        // 행 내용 구성
        row.innerHTML = `
            <td>
                <a href="#" class="show-detail" data-index="${index}">${item.product_code}</a>
            </td>
            <td>${item.product_name}</td>
            <td>${getStoreSelectHtml(item.store_id, index)}</td>
            <td>
                <input type="number" class="form-control form-control-sm cost-price" 
                       value="${item.cost_price}" min="0" step="0.01" data-index="${index}">
            </td>
            <td>
                <input type="number" class="form-control form-control-sm quantity" 
                       value="${item.quantity}" min="1" data-index="${index}">
            </td>
            <td class="item-total">${formatCurrency(item.cost_price * item.quantity)}</td>
            <td>
                <input type="text" class="form-control form-control-sm note" 
                       placeholder="비고" data-index="${index}">
            </td>
            <td>
                <button class="btn btn-sm btn-danger remove-btn" data-index="${index}">삭제</button>
            </td>
        `;
        
        tableBody.appendChild(row);
        
        // 이벤트 리스너 등록
        const costPriceInput = row.querySelector('.cost-price');
        const quantityInput = row.querySelector('.quantity');
        const noteInput = row.querySelector('.note');
        const removeBtn = row.querySelector('.remove-btn');
        const showDetailBtn = row.querySelector('.show-detail');
        const storeSelect = row.querySelector('.store-select');
        
        costPriceInput.addEventListener('change', function() {
            updateItemPrice(parseInt(this.dataset.index), parseFloat(this.value));
        });
        
        quantityInput.addEventListener('change', function() {
            updateItemQuantity(parseInt(this.dataset.index), parseInt(this.value));
        });
        
        noteInput.addEventListener('change', function() {
            const idx = parseInt(this.dataset.index);
            receiptItems[idx].note = this.value;
        });
        
        removeBtn.addEventListener('click', function() {
            removeItem(parseInt(this.dataset.index));
        });
        
        showDetailBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showProductDetail(parseInt(this.dataset.index));
        });
        
        if (storeSelect) {
            storeSelect.addEventListener('change', function() {
                const idx = parseInt(this.dataset.index);
                receiptItems[idx].store_id = parseInt(this.value);
            });
        }
    }
    
    // 행 업데이트
    function updateTableRow(index) {
        const item = receiptItems[index];
        const row = tableBody.querySelector(`tr[data-index="${index}"]`);
        
        if (row) {
            const quantityInput = row.querySelector('.quantity');
            const totalCell = row.querySelector('.item-total');
            
            quantityInput.value = item.quantity;
            totalCell.textContent = formatCurrency(item.cost_price * item.quantity);
        }
    }
    
    // 상품 가격 업데이트
    function updateItemPrice(index, price) {
        receiptItems[index].cost_price = price;
        updateTableRow(index);
        updateTotalAmount();
    }
    
    // 상품 수량 업데이트
    function updateItemQuantity(index, quantity) {
        receiptItems[index].quantity = quantity;
        updateTableRow(index);
        updateTotalAmount();
    }
    
    // 상품 제거
    function removeItem(index) {
        if (confirm('이 상품을 목록에서 제거하시겠습니까?')) {
            receiptItems.splice(index, 1);
            refreshTable();
            updateTotalAmount();
            
            if (receiptItems.length === 0) {
                emptyMessage.style.display = 'block';
                saveAllBtn.disabled = true;
            }
        }
    }
    
    // 테이블 전체 새로고침
    function refreshTable() {
        tableBody.innerHTML = '';
        
        receiptItems.forEach((item, index) => {
            item.index = index;
            addTableRow(index);
        });
    }
    
    // 총액 업데이트
    function updateTotalAmount() {
        const total = receiptItems.reduce((sum, item) => {
            return sum + (item.cost_price * item.quantity);
        }, 0);
        
        totalAmountEl.textContent = formatCurrency(total);
    }
    
    // 상품 상세 정보 표시
    function showProductDetail(index) {
        const item = receiptItems[index];
        const product = item.product_detail;
        
        // 모달 요소 참조
        const modalProductCode = document.getElementById('modal-product-code');
        const modalProductName = document.getElementById('modal-product-name');
        const modalProductCategory = document.getElementById('modal-product-category');
        const modalProductBarcode = document.getElementById('modal-product-barcode');
        const modalProductPrice = document.getElementById('modal-product-price');
        const productImage = document.getElementById('product-image');
        
        // 모달 내용 설정
        modalProductCode.textContent = product.code;
        modalProductName.textContent = product.name;
        modalProductCategory.textContent = product.category || '(없음)';
        modalProductBarcode.textContent = product.barcode;
        modalProductPrice.textContent = formatCurrency(product.current_price);
        
        if (product.image) {
            productImage.src = product.image;
            productImage.classList.remove('d-none');
        } else {
            productImage.src = '/static/inventory/img/no-image.png';
            productImage.classList.add('d-none');
        }
        
        // 모달 표시
        $('#productDetailModal').modal('show');
    }
    
    // 입고 정보 저장
    function saveAllReceipts() {
        if (receiptItems.length === 0) {
            alert('입고할 상품이 없습니다.');
            return;
        }
        
        if (!confirm('입력한 내용으로 입고 처리하시겠습니까?')) {
            return;
        }
        
        // 저장할 데이터 준비
        const receiptDate = receiptDateInput.value;
        const data = {
            receipts: receiptItems.map(item => ({
                product_id: item.product_id,
                store_id: item.store_id,
                quantity: item.quantity,
                cost_price: item.cost_price,
                note: item.note
            })),
            receipt_date: receiptDate
        };
        
        // 저장 버튼 비활성화 및 로딩 표시
        saveAllBtn.disabled = true;
        saveAllBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 저장 중...';
        
        // API 호출
        fetch('/inventory/api/save-stock-receipt/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            // 로딩 표시 제거
            saveAllBtn.disabled = false;
            saveAllBtn.innerHTML = '입고 처리 완료';
            
            if (data.success) {
                alert(data.message);
                // 입력 초기화
                receiptItems = [];
                tableBody.innerHTML = '';
                emptyMessage.style.display = 'block';
                totalAmountEl.textContent = '0원';
                saveAllBtn.disabled = true;
                barcodeInput.focus();
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('입고 정보 저장 중 오류가 발생했습니다.');
            saveAllBtn.disabled = false;
            saveAllBtn.innerHTML = '입고 처리 완료';
        });
    }
    
    // 유틸리티 함수
    
    // 매장 선택 HTML 생성
    function getStoreSelectHtml(storeId, index) {
        // 매장 목록이 서버에서 전달되어야 함
        const stores = getStoreList();
        
        if (stores.length <= 1) {
            // 매장이 하나뿐이면 선택 불가능
            return stores.length ? stores[0].name : '(매장 없음)';
        }
        
        let html = `<select class="form-control form-control-sm store-select" data-index="${index}">`;
        stores.forEach(store => {
            const selected = store.id === storeId ? 'selected' : '';
            html += `<option value="${store.id}" ${selected}>${store.name}</option>`;
        });
        html += '</select>';
        
        return html;
    }
    
    // 매장 목록 가져오기 (이 부분은 서버에서 전달받아야 함)
    function getStoreList() {
        // 이 함수는 서버에서 전달받은 매장 목록을 반환해야 함
        // 예시 데이터 - 실제로는 서버에서 전달받은 데이터를 사용
        return Array.from(document.querySelectorAll('#store option')).map(option => ({
            id: parseInt(option.value),
            name: option.textContent
        }));
    }
    
    // 기본 매장 ID 가져오기
    function getDefaultStoreId() {
        const stores = getStoreList();
        return stores.length > 0 ? stores[0].id : null;
    }
    
    // 금액 포맷팅
    function formatCurrency(amount) {
        return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(amount);
    }
    
    // CSRF 토큰 가져오기
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
    
    // 페이지 로드 시 바코드 입력란에 포커스
    barcodeInput.focus();
});