function generateQR() {
    const orderNum = document.getElementById('orderNumber').value;
    const qrContainer = document.getElementById('qr-result');
    
    if (!orderNum) {
        alert('يجب إدخال رقم العملية أولاً.');
        return;
    }

    qrContainer.innerHTML = '<span style="color: #007BFF;">جاري جلب بيانات الشحنة والتوليد...</span>';
    
    setTimeout(() => {
        const simulatedDbResponse = {
            id: orderNum,
            value: "1500 EGP"
        };
        
        const qrData = `PayDOD_ID:${simulatedDbResponse.id}|Value:${simulatedDbResponse.value}`; 
        const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(qrData)}`;
        
        qrContainer.innerHTML = `<img src="${qrUrl}" alt="QR Code">`;
    }, 500);
}
