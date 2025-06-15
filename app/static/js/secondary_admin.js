function assignRole(userId) {
    var selectedRole = $('#userRoleSelect').val();

    $.ajax({
        url: '/secondary_admin/assign-role/' + userId,
        method: 'POST',
        data: { role: selectedRole },
        success: function(response) {
            $('#roleAssignModal').modal('hide');
            
            if (typeof showNotification === 'function') {
                showNotification(response.message, 'success');
            } else {
                alert(response.message);
            }
            
            location.reload(); 
        },
        error: function(xhr) {
            var errorMessage = 'Ошибка при назначении роли';
            
            try {
                var response = JSON.parse(xhr.responseText);
                if (response && response.message) {
                    errorMessage = response.message;
                }
            } catch(e) {}
            
            if (typeof showNotification === 'function') {
                showNotification(errorMessage, 'danger');
            } else {
                alert(errorMessage);
            }
        }
    });
}

function initAdminCore() {
    function showNotification(message, type) {
        $('.custom-notification').remove();

        let bgColor, icon, title;
        switch(type) {
            case 'success':
                bgColor = 'linear-gradient(135deg, #1abc9c 0%, #16a085 100%)';
                icon = 'check-circle';
                title = 'Успешно';
                break;
            case 'danger':
                bgColor = 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)';
                icon = 'exclamation-circle';
                title = 'Ошибка';
                break;
            case 'warning':
                bgColor = 'linear-gradient(135deg, #f39c12 0%, #d35400 100%)';
                icon = 'exclamation-triangle';
                title = 'Внимание';
                break;
            case 'info':
            default:
                bgColor = 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)';
                icon = 'info-circle';
                title = 'Информация';
                break;
        }

        var notification = $(`
            <div class="custom-notification" style="
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1050;
                min-width: 300px;
                max-width: 400px;
                border-radius: 8px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
                overflow: hidden;
                background: white;
                transform: translateX(400px);
                opacity: 0;
                transition: all 0.3s ease-out;
            ">
                <div style="
                    background: ${bgColor};
                    color: white;
                    padding: 12px 15px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                ">
                    <div style="display: flex; align-items: center;">
                        <i class="fas fa-${icon}" style="font-size: 18px; margin-right: 10px;"></i>
                        <strong>${title}</strong>
                    </div>
                    <button type="button" class="close-notification" style="
                        background: none;
                        border: none;
                        color: white;
                        opacity: 0.8;
                        font-size: 20px;
                        cursor: pointer;
                        padding: 0;
                        line-height: 1;
                    ">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div style="
                    padding: 15px;
                    color: #333;
                    font-size: 14px;
                    line-height: 1.5;
                ">
                    ${message}
                </div>
                <div class="notification-progress" style="
                    height: 3px;
                    width: 100%;
                    background: rgba(255, 255, 255, 0.3);
                ">
                    <div style="
                        height: 100%;
                        width: 100%;
                        background: ${bgColor};
                        transition: width 5s linear;
                    "></div>
                </div>
            </div>
        `);

        $('body').append(notification);

        setTimeout(function() {
            notification.css({
                'transform': 'translateX(0)',
                'opacity': '1'
            });

            notification.find('.notification-progress > div').css('width', '0');
        }, 10);

        notification.find('.close-notification').on('click', function() {
            hideNotification(notification);
        });

        var timer = setTimeout(function() {
            hideNotification(notification);
        }, 5000);

        notification.hover(
            function() {
                clearTimeout(timer);
                notification.find('.notification-progress > div').css('transition', 'none');
            },
            function() {
                timer = setTimeout(function() {
                    hideNotification(notification);
                }, 5000);

                var progress = notification.find('.notification-progress > div');
                var currentWidth = progress.width() / progress.parent().width() * 100;
                var timeLeft = 5000 * (currentWidth / 100);

                progress.css({
                    'transition': `width ${timeLeft}ms linear`,
                    'width': '0'
                });
            }
        );

        function hideNotification(element) {
            element.css({
                'transform': 'translateX(400px)',
                'opacity': '0'
            });

            setTimeout(function() {
                element.remove();
            }, 300);
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        function scheduleModalNotification(message, type) {
            if (typeof showNotification === 'function') {
                showNotification(message, type);
            } else {
                alert(message);
            }
        }
        
        const copyToAllBtn = document.getElementById('copyToAllBtn');
        if (copyToAllBtn) {
            copyToAllBtn.addEventListener('click', function() {
                const mondayStart = document.getElementById('monday_start').value;
                const mondayEnd = document.getElementById('monday_end').value;
                
                if (mondayStart && mondayEnd) {
                    const days = ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
                    
                    days.forEach(day => {
                        document.getElementById(`${day}_start`).value = mondayStart;
                        document.getElementById(`${day}_end`).value = mondayEnd;
                    });
                    
                    scheduleModalNotification('Время скопировано на все дни', 'success');
                } else {
                    scheduleModalNotification('Сначала укажите время для понедельника', 'warning');
                }
            });
        }
        
        const workdaysOnlyBtn = document.getElementById('workdaysOnlyBtn');
        if (workdaysOnlyBtn) {
            workdaysOnlyBtn.addEventListener('click', function() {
                const workdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
                const weekend = ['saturday', 'sunday'];
                
                workdays.forEach(day => {
                    const elem = document.getElementById(day);
                    if (elem) elem.checked = true;
                });
                
                weekend.forEach(day => {
                    const elem = document.getElementById(day);
                    if (elem) elem.checked = false;
                });
                
                scheduleModalNotification('Активированы только рабочие дни', 'success');
            });
        }
        
        document.querySelectorAll('input[type="time"]').forEach(input => {
            input.addEventListener('change', function() {
                const dayId = this.id.split('_')[0];
                const checkbox = document.getElementById(dayId);
                
                if (this.value && checkbox && !checkbox.checked) {
                    checkbox.checked = true;
                }
            });
        });
    });
    
    const saveScheduleBtnHandler = function() {
        function saveScheduleNotification(message, type) {
            if (typeof showNotification === 'function') {
                showNotification(message, type);
            } else {
                alert(message);
            }
        }
        
        const schedule = [];
        const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
        let hasError = false;
        
        days.forEach(day => {
            const checkbox = document.getElementById(day);
            
            if (checkbox && checkbox.checked) {
                const dayOfWeek = parseInt(checkbox.value);
                const startTime = document.getElementById(`${day}_start`).value;
                const endTime = document.getElementById(`${day}_end`).value;
                
                if (!startTime || !endTime) {
                    saveScheduleNotification(`Укажите время начала и окончания для ${day}`, 'warning');
                    hasError = true;
                    return;
                }
                
                schedule.push({ day_of_week: dayOfWeek, start_time: startTime, end_time: endTime });
            }
        });
        
        if (hasError) return;
        
        if (schedule.length === 0) {
            saveScheduleNotification('Активируйте хотя бы один день недели', 'warning');
            return;
        }
        
        const scheduleData = { schedule };
        
        $.ajax({
            url: `/secondary_admin/service/${currentServiceId}/schedule`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(scheduleData),
            success: function(response) {
                if (response.status === 'success') {
                    $('#scheduleServiceModal').modal('hide');
                    saveScheduleNotification('Расписание успешно обновлено', 'success');
                } else {
                    saveScheduleNotification('Ошибка при обновлении расписания: ' + response.message, 'danger');
                }
            },
            error: function(xhr) {
                saveScheduleNotification('Ошибка при сохранении расписания', 'danger');
            }
        });
    };
    
    let currentServiceId = null;

    document.querySelectorAll('.schedule-service-btn').forEach(button => {
        button.addEventListener('click', function() {
            const serviceId = this.getAttribute('data-service-id');
            currentServiceId = serviceId;
            fetch(`/secondary_admin/service/${serviceId}/schedule`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const planNameElement = document.getElementById('planName');
                        if (planNameElement) planNameElement.value = data.planName;
                        const schedules = data.schedules;
                        document.querySelectorAll('.form-check input[type="checkbox"]').forEach(checkbox => {
                            checkbox.checked = false;
                            const startElement = document.getElementById(`${checkbox.id}_start`);
                            const endElement = document.getElementById(`${checkbox.id}_end`);
                            if (startElement) startElement.value = '';
                            if (endElement) endElement.value = '';
                        });
                        schedules.forEach(schedule => {
                            const dayCheckbox = document.querySelector(`input[value="${schedule.day_of_week}"]`);
                            if (dayCheckbox) {
                                dayCheckbox.checked = true;
                                const startTimeInput = document.getElementById(`${dayCheckbox.id}_start`);
                                const endTimeInput = document.getElementById(`${dayCheckbox.id}_end`);
                                if (startTimeInput) startTimeInput.value = schedule.start_time;
                                if (endTimeInput) endTimeInput.value = schedule.end_time;
                            }
                        });
                        $('#scheduleServiceModal').modal('show');
                    }
                })
                .catch(error => {});
        });
    });
	
    const saveScheduleBtn = document.getElementById('saveScheduleBtn');
    if (saveScheduleBtn) {
        const newSaveScheduleBtn = saveScheduleBtn.cloneNode(true);
        saveScheduleBtn.parentNode.replaceChild(newSaveScheduleBtn, saveScheduleBtn);
        newSaveScheduleBtn.addEventListener('click', saveScheduleBtnHandler);
    }
	
    $(document).ready(function() {
        if (!localStorage.getItem('licenseAccepted')) {
            $('#licenseModal').modal({
                backdrop: 'static',
                keyboard: false
            });
        }

        $('#acceptLicense').click(function() {
            localStorage.setItem('licenseAccepted', 'true');
            $('#licenseModal').modal('hide');
        });

        $('#declineLicense').click(function() {
            localStorage.removeItem('licenseAccepted');
            window.location.href = '/logout';
        });

        $('#logout').click(function() {
            localStorage.removeItem('licenseAccepted');
        });
        
        $("#userSearchInput").on("keyup", function() {
            var value = $(this).val().toLowerCase();
            $(".user-row").filter(function() {
                $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
            });
        });
        
        $("#serviceSearchInput").on("keyup", function() {
            var value = $(this).val().toLowerCase();
            $("#servicesList tr").filter(function() {
                $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
            });
        });
        
        $('.toggle-group').click(function() {
            var groupId = $(this).data('group-id');
            var $groupUsers = $('.group-' + groupId);
            var $icon = $(this).find('i');
            
            if ($groupUsers.is(':visible')) {
                $groupUsers.slideUp(100);
                $icon.removeClass('fa-minus').addClass('fa-plus');
                $groupUsers.removeClass('highlighted-group');
            } else {
                $groupUsers.slideDown(300);
                $icon.removeClass('fa-plus').addClass('fa-minus');
                $groupUsers.addClass('highlighted-group');
            }
        });
        
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", $('meta[name="csrf-token"]').attr('content'));
                }
            }
        });

        $('input[name="csrf_token"]:gt(0)').remove();

        function saveActiveTab() {
            localStorage.setItem('activeTab', $('.nav-pills .nav-link.active').attr('id'));
        }

        var activeTab = localStorage.getItem('activeTab');
        if (activeTab) {
            $('#' + activeTab).tab('show');
        }

        $('a[data-toggle="pill"]').on('shown.bs.tab', function(e) {
            saveActiveTab();
        });
        
        $('.show-dependencies-btn, .assign-service-btn').off('click').on('click', function() {
            var userId = $(this).data('user-id');
            $('#userIdField').val(userId);
            loadUserServices(userId);
            $('#assigned-services-tab').tab('show');
            $('#userServicesModal').modal('show');
        });
        
        function loadUserServices(userId) {
            $('#loadingServices').show();
            $('#noAssignedServices').hide();
            $('#userServicesList .service-item').remove();
            
            $.ajax({
                url: `/secondary_admin/user_service_tree/${userId}`,
                method: 'GET',
                success: function(data) {
                    $('#loadingServices').hide();
                    
                    if (data.length > 0) {
                        var servicesList = $('#userServicesList');
                        
                        data.forEach(function(item) {
                            servicesList.append(`
                                <div class="service-item" data-service-name="${item.service.toLowerCase()}">
                                    <div class="service-header">
                                        <h5 class="service-name">${item.service}</h5>
                                        <div class="service-actions">
                                            <button class="btn btn-danger btn-sm delete-service-btn" data-assignment-id="${item.assignmentId}">
                                                <i class="fas fa-trash-alt"></i> Удалить
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            `);
                        });
                    } else {
                        $('#noAssignedServices').show();
                    }
                    
                    $('#available-services-tab').off('shown.bs.tab').on('shown.bs.tab', function() {
                        loadAvailableServices(userId);
                    });
                },
                error: function(xhr) {
                    $('#loadingServices').hide();
                    $('#noAssignedServices').show();
                    showNotification('Ошибка при загрузке услуг пользователя', 'danger');
                }
            });
        }
        
        function loadAvailableServices(userId) {
            $('#loadingAvailableServices').show();
            $('#noAvailableServices').hide();
            $('#availableServicesList .available-service-card').remove();
            
            $.ajax({
                url: '/secondary_admin/load-services',
                method: 'GET',
                success: function(allServices) {
                    $.ajax({
                        url: `/secondary_admin/user_service_tree/${userId}`,
                        method: 'GET',
                        success: function(assignedServices) {
                            $('#loadingAvailableServices').hide();
                            
                            const assignedServiceIds = assignedServices.map(item => item.serviceId);
                            const availableServices = allServices.filter(service => 
                                !assignedServices.some(assigned => assigned.service === service.name)
                            );
                            
                            if (availableServices.length > 0) {
                                const availableServicesList = $('#availableServicesList');
                                
                                availableServices.forEach(function(service) {
                                    availableServicesList.append(`
                                        <div class="available-service-card" data-service-id="${service.id}" data-service-name="${service.name.toLowerCase()}">
                                            <div class="service-info">
                                                <h6 class="service-title">${service.name}</h6>
                                                <div class="service-select-indicator">
                                                    <i class="fas fa-check-circle"></i>
                                                </div>
                                            </div>
                                        </div>
                                    `);
                                });
                                
                                $('.available-service-card').off('click').on('click', function() {
                                    $(this).toggleClass('selected');
                                });
                            } else {
                                $('#noAvailableServices').show();
                            }
                        },
                        error: function(xhr) {
                            $('#loadingAvailableServices').hide();
                            $('#noAvailableServices').show();
                            showNotification('Ошибка при загрузке назначенных услуг', 'danger');
                        }
                    });
                },
                error: function(xhr) {
                    $('#loadingAvailableServices').hide();
                    $('#noAvailableServices').show();
                    showNotification('Ошибка при загрузке списка услуг', 'danger');
                }
            });
        }
        
        $('#assignSelectedServices').off('click').on('click', function() {
            const userId = $('#userIdField').val();
            const selectedServices = $('.available-service-card.selected');
            
            if (selectedServices.length === 0) {
                showNotification('Выберите хотя бы одну услугу для назначения', 'warning');
                return;
            }
            
            let assignedCount = 0;
            let errorCount = 0;
            let totalToAssign = selectedServices.length;
            
            selectedServices.each(function() {
                const serviceId = $(this).data('service-id');
                
                $.ajax({
                    url: '/secondary_admin/assign_service_to_user',
                    method: 'POST',
                    data: {
                        user_id: userId,
                        service_id: serviceId
                    },
                    success: function(response) {
                        assignedCount++;
                        checkCompletion();
                    },
                    error: function(xhr) {
                        errorCount++;
                        checkCompletion();
                    }
                });
            });
            
            function checkCompletion() {
                if (assignedCount + errorCount === totalToAssign) {
                    if (errorCount === 0) {
                        showNotification(`Успешно назначено ${assignedCount} услуг`, 'success');
                    } else if (assignedCount > 0) {
                        showNotification(`Назначено ${assignedCount} услуг, ${errorCount} с ошибками`, 'warning');
                    } else {
                        showNotification('Ошибка при назначении услуг', 'danger');
                    }
                    
                    $('#assigned-services-tab').tab('show');
                    loadUserServices(userId);
                }
            }
        });
        
        $('#searchAssignedServices').off('keyup').on('keyup', function() {
            const searchValue = $(this).val().toLowerCase();
            
            $('.service-item').each(function() {
                const serviceName = $(this).data('service-name');
                $(this).toggle(serviceName.indexOf(searchValue) > -1);
            });
            
            const visibleServices = $('.service-item:visible').length;
            if (visibleServices === 0 && $('.service-item').length > 0) {
                if (!$('#noMatchingServices').length) {
                    $('#userServicesList').append(`
                        <div id="noMatchingServices" class="text-center p-4">
                            <i class="fas fa-search fa-2x mb-3"></i>
                            <p>Нет услуг, соответствующих поиску</p>
                        </div>
                    `);
                } else {
                    $('#noMatchingServices').show();
                }
            } else {
                $('#noMatchingServices').hide();
            }
        });
        
        $('#searchAvailableServices').off('keyup').on('keyup', function() {
            const searchValue = $(this).val().toLowerCase();
            
            $('.available-service-card').each(function() {
                const serviceName = $(this).data('service-name');
                $(this).toggle(serviceName.indexOf(searchValue) > -1);
            });
            
            const visibleServices = $('.available-service-card:visible').length;
            if (visibleServices === 0 && $('.available-service-card').length > 0) {
                if (!$('#noMatchingAvailableServices').length) {
                    $('#availableServicesList').append(`
                        <div id="noMatchingAvailableServices" class="text-center p-4">
                            <i class="fas fa-search fa-2x mb-3"></i>
                            <p>Нет доступных услуг, соответствующих поиску</p>
                        </div>
                    `);
                } else {
                    $('#noMatchingAvailableServices').show();
                }
            } else {
                $('#noMatchingAvailableServices').hide();
            }
        });

        $(document).off('click', '.delete-service-btn').on('click', '.delete-service-btn', function() {
            const assignmentId = $(this).data('assignment-id');
            const serviceItem = $(this).closest('.service-item');
            const serviceName = serviceItem.find('.service-name').text();
            
            if (confirm(`Вы уверены, что хотите удалить назначение услуги "${serviceName}"?`)) {
                $.ajax({
                    url: `/secondary_admin/delete_service_assignment/${assignmentId}`,
                    method: 'POST',
                    success: function(response) {
                        showNotification('Назначение услуги успешно удалено', 'success');
                        
                        serviceItem.fadeOut(300, function() {
                            $(this).remove();
                            
                            if ($('.service-item').length === 0) {
                                $('#noAssignedServices').show();
                            }
                            
                            if ($('#available-services-tab').hasClass('active')) {
                                const userId = $('#userIdField').val();
                                loadAvailableServices(userId);
                            }
                        });
                    },
                    error: function(xhr) {
                        showNotification('Ошибка при удалении назначения услуги', 'danger');
                    }
                });
            }
        });

        $('#addUserModal form').submit(function(e) {
            e.preventDefault();
            
            var formData = $(this).serialize();
            var username = $(this).find('input[name="username"]').val().trim();
            
            $.ajax({
                url: $(this).attr('action'),
                method: 'POST',
                data: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                success: function(response) {
                    $('#addUserModal').modal('hide');
                    
                    var message = 'Пользователь успешно добавлен';
                    if (response && response.message) {
                        message = response.message;
                    }
                    
                    showNotification(message, 'success');
                    
                    $('#addUserModal form')[0].reset();
                    
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                },
                error: function(xhr) {
                    var errorMessage = 'Ошибка при добавлении пользователя';
                    
                    try {
                        var response = JSON.parse(xhr.responseText);
                        if (response && response.message) {
                            errorMessage = response.message;
                        }
                    } catch(e) {
                        if (xhr.status === 400) {
                            errorMessage = 'Ошибка валидации данных';
                        } else if (xhr.status === 500) {
                            if (xhr.responseText.includes('UNIQUE constraint failed')) {
                                errorMessage = 'Пользователь с таким именем уже существует. Выберите другое имя.';
                            } else {
                                errorMessage = 'Внутренняя ошибка сервера';
                            }
                        }
                    }
                    
                    showNotification(errorMessage, 'danger');
                }
            });
        });

        function loadVideoFolders(callback) {
            $.ajax({
                url: '/secondary_admin/get_video_folders',
                method: 'GET',
                success: function(response) {
                    if (response.status === 'success') {
                        var folderSelect = $('#editVideoFolder');
                        var currentValue = folderSelect.val();
                        
                        folderSelect.empty();
                        
                        response.folders.forEach(function(folder) {
                            const folderValue = folder === 'default' ? '/' : folder;
                            const folderText = folder === 'default' ? 'Корневая папка' : folder;
                            folderSelect.append(`<option value="${folderValue}">${folderText}</option>`);
                        });
                        
                        if (currentValue && folderSelect.find(`option[value="${currentValue}"]`).length) {
                            folderSelect.val(currentValue);
                        }
                        
                        if (typeof callback === 'function') {
                            callback();
                        }
                        
                    } else {
                        showNotification('Ошибка при получении списка папок', 'warning');
                    }
                },
                error: function(xhr) {
                    showNotification('Ошибка при загрузке списка папок: ' + xhr.statusText, 'danger');
                }
            });
        }

        var userId; 

        $('#editUserModal').on('show.bs.modal', function(event) {
            var button = $(event.relatedTarget);
            userId = button.data('id');
            var username = button.data('username');
            var role = button.data('role');
            var cabinet = button.data('cabinet');
            var video = button.data('video');
            var marqueeText = button.data('marquee-text');

            var modal = $(this);
            modal.find('#editUserId').val(userId);
            modal.find('#editUsername').val(username);
            modal.find('#editRole').val(role); 
            modal.find('#editCabinet').val(cabinet);
            modal.find('#editPassword').val('');
            
            // Показываем поле бегущей строки для табло
            if (role === 'tablo') {
                $('#marqueeTextContainer').slideDown();
                $('#editMarqueeText').val(marqueeText || '');
                $('#videoSettingsContainer').slideDown();
                
                loadVideoFolders(function() {
                    var showVideo = video && video !== '0' && video !== '';
                    $('#editShowVideo').prop('checked', showVideo);

                    if (showVideo) {
                        $('#videoFolderContainer').show();
                        $('#editVideoFolder').val(video);
                    } else {
                        $('#videoFolderContainer').hide();
                    }
                });
            } else {
                $('#marqueeTextContainer').slideUp();
                $('#videoSettingsContainer').slideUp();
            }
        });

        // Обработчик изменения роли в форме редактирования
        $(document).on('change', '#editRole', function() {
            if ($(this).val() === 'tablo') {
                $('#marqueeTextContainer').slideDown();
                $('#videoSettingsContainer').slideDown();
                loadVideoFolders();
            } else {
                $('#marqueeTextContainer').slideUp();
                $('#videoSettingsContainer').slideUp();
            }
        });

        $(document).on('change', '#addUserRole', function() {
            if ($(this).val() === 'tablo') {
                $('#addMarqueeTextContainer').slideDown();
            } else {
                $('#addMarqueeTextContainer').slideUp();
            }
        });

        $(document).on('change', '#editShowVideo', function() {
            if ($(this).is(':checked')) {
                $('#videoFolderContainer').slideDown();
                loadVideoFolders();
            } else {
                $('#videoFolderContainer').slideUp();
                $('#editVideoFolder').val('default');
            }
        });

        $(document).on('click', '.refresh-folders-btn', function() {
            loadVideoFolders();
        });

        $('#editUserForm').on('submit', function(e) {
            e.preventDefault();
            userId = $('#editUserId').val();
            var username = $('#editUsername').val();
            var role = $('#editRole').val(); 
            var cabinet = $('#editCabinet').val();
            var password = $('#editPassword').val();
            
            var videoValue = '0';
            if (role === 'tablo' && $('#editShowVideo').is(':checked')) {
                videoValue = $('#editVideoFolder').val() || '/'; 
            }
            
            var marqueeText = role === 'tablo' ? $('#editMarqueeText').val() : '';
            
            var data = {
                username: username,
                role: role,
                cabinet: cabinet,
                video: videoValue,
                marquee_text: marqueeText
            };

            if (password) {
                data.password = password;
            }

            $.ajax({
                url: '/secondary_admin/edit-user/' + userId,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(data),
                success: function(response) {
                    $('#editUserModal').modal('hide');
                    showNotification('Пользователь успешно отредактирован', 'success');
                    location.reload();
                },
                error: function(xhr, status, error) {
                    var errorMessage = 'Произошла ошибка при редактировании пользователя';
                    try {
                        var response = JSON.parse(xhr.responseText);
                        if (response.message) {
                            errorMessage = response.message;
                        }
                    } catch(e) {}
                    showNotification(errorMessage, 'danger');
                }
            });
        });  

        var serviceId; 

        $('.edit-service-btn').click(function() {
            serviceId = $(this).data('service-id');
            var serviceName = $(this).data('service-name');
            var startNumber = $(this).data('start-number');
            var endNumber = $(this).data('end-number');
            var cabinet = $(this).data('cabinet');

            $('#editServiceId').val(serviceId);
            $('#editServiceName').val(serviceName);
            $('#editStartNumber').val(startNumber);
            $('#editEndNumber').val(endNumber);
            $('#editCabinetNumber').val(cabinet);

            $('#editServiceModal').modal('show');
        });

        $('#editServiceForm').on('submit', function(e) {
            e.preventDefault();
            serviceId = $('#editServiceId').val();
            var serviceName = $('#editServiceName').val();
            var startNumber = $('#editStartNumber').val();
            var endNumber = $('#editEndNumber').val();
            var cabinet = $('#editCabinetNumber').val();

            $.ajax({
                url: '/secondary_admin/edit-service/' + serviceId,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    name: serviceName,
                    start_number: startNumber,
                    end_number: endNumber,
                    cabinet: cabinet
                }),
                success: function(response) {
                    $('#editServiceModal').modal('hide');
                    showNotification('Услуга успешно отредактирована', 'success');
                    location.reload();
                },
                error: function(xhr, status, error) {
                    showNotification('Произошла ошибка при редактировании услуги', 'danger');
                }
            });
        });

        $('#addServiceForm').on('submit', function(e) {
            e.preventDefault();

            $.ajax({
                url: '/secondary_admin/add-service',
                method: 'POST',
                data: $(this).serialize(),
                success: function(response) {
                    if (response.status === 'success') {
                        $('#addServiceModal').modal('hide');
                        showNotification('Услуга успешно добавлена', 'success');
                        saveActiveTab();
                        location.reload();
                    } else {
                        showNotification(response.message, 'danger');
                    }
                },
                error: function(xhr) {
                    showNotification('Ошибка при добавлении услуги: ' + xhr.responseText, 'danger');
                }
            });
        });

        $('.delete-user-btn').click(function(e) {
            e.preventDefault();
            var userId = $(this).data('user-id');
            if (confirm('Вы уверены, что хотите удалить этого пользователя?')) {
                $.ajax({
                    url: `/secondary_admin/delete-user/${userId}`,
                    method: 'POST',
                    success: function(response) {
                        showNotification('Пользователь удален', 'success');
                        location.reload();
                    },
                    error: function() {
                        showNotification('Ошибка при удалении пользователя', 'danger');
                    }
                });
            }
        });

        $('#servicesList').on('click', '.delete-service-btn', function() {
            var serviceId = $(this).data('service-id');
            if (confirm('Вы уверены, что хотите удалить эту услугу?')) {
                $.ajax({
                    url: '/secondary_admin/delete-service/' + serviceId,
                    method: 'POST',
                    success: function(response) {
                        showNotification(response.message, 'success');
                        $('#serviceRow' + serviceId).remove();
                    },
                    error: function(xhr) {
                        showNotification('Ошибка при удалении услуги: ' + xhr.responseText, 'danger');
                    }
                });
            }
        });

        $('.delete-all-tickets-btn').on('click', function() {
            const serviceId = $(this).data('service-id');
            if (confirm('Вы уверены, что хотите удалить все тикеты для этой услуги?')) {
                $.ajax({
                    url: `/secondary_admin/delete_all_tickets/${serviceId}`,
                    type: 'POST',
                    success: function(response) {
                        showNotification(response.message, 'success');
                        location.reload();
                    },
                    error: function(xhr) {
                        let errorMsg = JSON.parse(xhr.responseText).message;
                        showNotification('Ошибка при удалении тикетов: ' + errorMsg, 'danger');
                    }
                });
            }
        });
           
        $('#changePasswordModal').on('show.bs.modal', function (event) {
            var button = $(event.relatedTarget);
            var userId = button.data('user-id');
            var csrfToken = $('meta[name="csrf-token"]').attr('content');
            var modal = $(this);
            modal.find('#changePasswordUserId').val(userId);
            modal.find('#csrfToken').val(csrfToken);
        });

        $('#changePasswordForm').on('submit', function(e) {
            e.preventDefault();
            var userId = $('#changePasswordUserId').val();
            var newPassword = $('#new_password').val();
            var confirmNewPassword = $('#confirm_new_password').val();
            var csrfToken = $('#csrfToken').val();

            if (newPassword !== confirmNewPassword) {
                showNotification('Пароли не совпадают', 'warning');
                return;
            }

            $.ajax({
                url: '/secondary_admin/change-password',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    user_id: userId,
                    new_password: newPassword,
                    confirm_new_password: confirmNewPassword,
                    csrf_token: csrfToken
                }),
                success: function(response) {
                    $('#changePasswordModal').modal('hide');
                    showNotification(response.message, 'success');
                },
                error: function(xhr, status, error) {
                    showNotification('Произошла ошибка при смене пароля: ' + xhr.responseJSON.message, 'danger');
                }
            });
        });

        var selectedUsers = [];

        $('#groupUsersBtn').click(function() {
            selectedUsers = [];
            $('.user-checkbox:checked').each(function() {
                selectedUsers.push($(this).data('user-id'));
            });

            if (selectedUsers.length > 0) {
                $('#groupModal').modal('show');
            } else {
                showNotification('Выберите хотя бы одного пользователя', 'warning');
            }
        });

        $('#groupForm').submit(function(e) {
            e.preventDefault();

            var groupName = $('#groupName').val();
            var groupData = {
                name: groupName,
                users: selectedUsers
            };

            $.ajax({
                url: '/secondary_admin/save_group',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(groupData),
                success: function(response) {
                    showNotification('Группа успешно создана', 'success');
                    $('#groupModal').modal('hide');
                    location.reload();
                },
                error: function(xhr) {
                    showNotification('Ошибка при создании группы: ' + xhr.responseText, 'danger');
                }
            });
        });

        $('.delete-group-btn').click(function() {
            var groupId = $(this).data('group-id');
            if (confirm('Вы уверены, что хотите удалить эту группу?')) {
                $.ajax({
                    url: '/secondary_admin/elete_group',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ group_id: groupId }),
                    success: function(response) {
                        showNotification('Группа успешно удалена', 'success');
                        location.reload();
                    },
                    error: function(xhr) {
                        showNotification('Ошибка при удалении группы: ' + xhr.responseText, 'danger');
                    }
                });
            }
        });
    });    
}

$(document).ready(function() {
    initAdminCore();
});

$(function() {
    $(document).off('click', '#copyToAllBtn');
    $(document).off('click', '#workdaysOnlyBtn');
    $('#copyToAllBtn').off('click');
    $('#workdaysOnlyBtn').off('click');
    
    $(document).on('click', '#copyToAllBtn', function(e) {
        e.preventDefault();
        
        const mondayStart = $('#monday_start').val();
        const mondayEnd = $('#monday_end').val();
        
        if (mondayStart && mondayEnd) {
            const days = ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
            
            days.forEach(day => {
                $(`#${day}_start`).val(mondayStart);
                $(`#${day}_end`).val(mondayEnd);
            });
            
            if (typeof showNotification === 'function') {
                showNotification('Время скопировано на все дни', 'success');
            } else {
                alert('Время скопировано на все дни');
            }
        } else {
            if (typeof showNotification === 'function') {
                showNotification('Сначала укажите время для понедельника', 'warning');
            } else {
                alert('Сначала укажите время для понедельника');
            }
        }
    });
    
    $(document).on('click', '#workdaysOnlyBtn', function(e) {
        e.preventDefault();
        
        const workdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
        const weekend = ['saturday', 'sunday'];
        
        workdays.forEach(day => {
            $(`#${day}`).prop('checked', true);
        });
        
        weekend.forEach(day => {
            $(`#${day}`).prop('checked', false);
        });
        
        if (typeof showNotification === 'function') {
            showNotification('Активированы только рабочие дни', 'success');
        } else {
            alert('Активированы только рабочие дни');
        }
    });
    
    $(document).on('change', 'input[type="time"]', function() {
        const dayId = this.id.split('_')[0];
        const checkbox = $(`#${dayId}`);
        
        if (this.value && checkbox.length && !checkbox.prop('checked')) {
            checkbox.prop('checked', true);
        }
    });
});