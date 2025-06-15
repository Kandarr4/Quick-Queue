function loadDiskSpaceInfo() {

    const diskSpaceInfo = document.getElementById('disk-space-info');
    const refreshBtn = document.getElementById('refreshDiskSpaceBtn');
    
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Обновление...';
    }
    const csrfToken = $('meta[name=csrf-token]').attr('content');

    $.ajax({
        url: '/secondary_admin/get_disk_space',
        method: 'GET',
        xhrFields: {
            withCredentials: true
        },
        beforeSend: function(xhr) {
            if (csrfToken) {
                xhr.setRequestHeader('X-CSRFToken', csrfToken);
            }
        },
        success: function(response) {

            if (response.status === 'success' && diskSpaceInfo) {
                const usedPercentage = response.used_percentage;
                const progressBarColor = usedPercentage > 90 ? 'bg-danger' : 
                                        usedPercentage > 75 ? 'bg-warning' : 
                                        'bg-success';

                diskSpaceInfo.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="flex-grow-1 mr-3">
                            <div class="progress" style="height: 20px;">
                                <div class="progress-bar ${progressBarColor}" 
                                    role="progressbar" 
                                    style="width: ${usedPercentage}%;" 
                                    aria-valuenow="${usedPercentage}" 
                                    aria-valuemin="0" 
                                    aria-valuemax="100">
                                    ${usedPercentage}%
                                </div>
                            </div>
                        </div>
                        <div>
                            <small>
                                <strong>Всего:</strong> ${response.total_readable} | 
                                <strong>Занято:</strong> ${response.used_readable} | 
                                <strong>Свободно:</strong> ${response.free_readable}
                            </small>
                        </div>
                        <button id="refreshDiskSpaceBtn" class="btn btn-sm btn-outline-secondary ml-2">
                            <i class="fas fa-sync-alt"></i> Обновить
                        </button>
                    </div>
                `;
            }
        },
        error: function(xhr, status, error) {

            let errorMessage = 'Неизвестная ошибка';
            try {
                const response = JSON.parse(xhr.responseText);
                errorMessage = response.message || response.trace || errorMessage;
            } catch(e) {
                errorMessage = xhr.responseText || error;
            }

            if (diskSpaceInfo) {
                diskSpaceInfo.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="alert alert-danger flex-grow-1 mr-2 mb-0">
                            <i class="fas fa-exclamation-triangle mr-2"></i>
                            Не удалось загрузить информацию о диске: ${errorMessage}
                        </div>
                        <button id="refreshDiskSpaceBtn" class="btn btn-sm btn-outline-secondary">
                            <i class="fas fa-sync-alt"></i> Обновить
                        </button>
                    </div>
                `;
            }
        },
        complete: function() {
            const refreshBtn = document.getElementById('refreshDiskSpaceBtn');
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Обновить';
                refreshBtn.removeEventListener('click', loadDiskSpaceInfo);
                refreshBtn.addEventListener('click', loadDiskSpaceInfo);
            }
        }
    });
}
function initAdminVideo() {
    let currentPath = '';
    const folderTemplate = document.getElementById('folder-card-template');
    const videoTemplate = document.getElementById('video-card-template');
    const foldersContainer = document.getElementById('folders-container');
    const videosContainer = document.getElementById('videos-container');
    const noFoldersMessage = document.getElementById('no-folders-message');
    const noVideosMessage = document.getElementById('no-videos-message');
    const currentPathDisplay = document.getElementById('current-path');
    const breadcrumbPath = document.getElementById('breadcrumb-path');
    const folderInfoText = document.getElementById('folder-info-text');
    const fileCountText = document.getElementById('file-count-text');
    const folderCountText = document.getElementById('folder-count-text');
    const currentDirForNewFolder = document.getElementById('current-dir-for-new-folder');
    const currentDirForUpload = document.getElementById('current-dir-for-upload');
    function showVideoNotification(message, type) {
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            alert(message);
        }
    }
    function updatePathDisplay() {
        if (currentPathDisplay) currentPathDisplay.textContent = currentPath || '/';
        if (currentDirForNewFolder) currentDirForNewFolder.textContent = currentPath || '/';
        if (currentDirForUpload) currentDirForUpload.textContent = currentPath || '/';
        if (folderInfoText) folderInfoText.innerHTML = `Текущая директория: <strong>${currentPath || '/'}</strong>`;
        
        updateBreadcrumbs();
        
        try {
            localStorage.setItem('videoCurrentPath', currentPath);
        } catch (e) {
        }
    }
    function updateBreadcrumbs() {
        if (!breadcrumbPath) return;
        
        breadcrumbPath.innerHTML = '';
        
        if (!currentPath) return;
        
        const segments = currentPath.split('/').filter(Boolean);
        let path = '';
        
        segments.forEach((segment, index) => {
            path += (index > 0 ? '/' : '') + segment;
            const isLast = index === segments.length - 1;
            
            const listItem = document.createElement('li');
            listItem.className = 'breadcrumb-item';
            
            if (isLast) {
                listItem.className += ' active';
                listItem.textContent = segment;
            } else {
                const link = document.createElement('a');
                link.href = '#';
                link.className = 'folder-link';
                link.setAttribute('data-path', path);
                link.textContent = segment;
                listItem.appendChild(link);
            }
            
            breadcrumbPath.appendChild(listItem);
        });
    }
    function loadDirectoryContents(path = '') {
        currentPath = path;
        if (foldersContainer) {
            foldersContainer.innerHTML = '<div class="col-12 text-center py-3"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Загрузка...</p></div>';
        }
        if (videosContainer) {
            videosContainer.innerHTML = '';
        }
        updatePathDisplay();
        const csrfToken = $('meta[name=csrf-token]').attr('content');
        $.ajax({
            url: '/secondary_admin/get_directory_contents',
            method: 'GET',
            data: { path: path },
            beforeSend: function(xhr) {
                if (csrfToken) {
                    xhr.setRequestHeader('X-CSRFToken', csrfToken);
                }
            },
            success: function(response) {
                if (response.status === 'success') {
                    renderDirectoryContents(response.data);
                } else {
                    showVideoNotification('Ошибка при загрузке содержимого директории: ' + response.message, 'danger');
                }
            },
            error: function(xhr) {
                showVideoNotification('Ошибка при загрузке содержимого директории', 'danger');
            }
        });
    }
    function renderDirectoryContents(data) {
        if (!data || !data.folders || !data.files) {
            showVideoNotification('Неверная структура данных', 'danger');
            return;
        }
        if (fileCountText) fileCountText.textContent = `Файлов: ${data.files.length}`;
        if (folderCountText) folderCountText.textContent = `Папок: ${data.folders.length}`;
        if (foldersContainer) foldersContainer.innerHTML = '';
        if (videosContainer) videosContainer.innerHTML = '';
        if (data.folders.length === 0) {
            if (foldersContainer) {
                foldersContainer.innerHTML = `
                    <div id="no-folders-message" class="col-12 text-center py-3">
                        <i class="fas fa-folder-open fa-2x mb-2" style="opacity: 0.5;"></i>
                        <p>Нет папок в текущей директории</p>
                    </div>
                `;
            }
        } else {
            data.folders.forEach(folder => {
                renderFolderCard(folder);
            });
        }
        if (data.files.length === 0) {
            if (videosContainer) {
                videosContainer.innerHTML = `
                    <div id="no-videos-message" class="col-12 text-center py-3">
                        <i class="fas fa-film fa-2x mb-2" style="opacity: 0.5;"></i>
                        <p>Нет видеофайлов в текущей директории</p>
                    </div>
                `;
            }
        } else {
            data.files.forEach(file => {
                renderVideoCard(file);
            });
        }
        updateFoldersList();
    }
    function renderFolderCard(folder) {
        if (!folderTemplate || !foldersContainer) return;
        
        const folderCard = folderTemplate.content.cloneNode(true);
        const folderNameText = folderCard.querySelector('.folder-name-text');
        const folderInfoText = folderCard.querySelector('.folder-info');
        const openFolderBtn = folderCard.querySelector('.open-folder');
        const renameBtn = folderCard.querySelector('.rename-folder');
        const moveBtn = folderCard.querySelector('.move-folder');
        const deleteBtn = folderCard.querySelector('.delete-folder');
        
        if (folderNameText) folderNameText.textContent = folder.name;
        if (folderInfoText) folderInfoText.textContent = `Создана: ${folder.created || 'Н/Д'}`;
        const folderPath = currentPath ? `${currentPath}/${folder.name}` : folder.name;
        if (openFolderBtn) openFolderBtn.setAttribute('data-path', folderPath);
        if (renameBtn) renameBtn.setAttribute('data-path', folderPath);
        if (moveBtn) moveBtn.setAttribute('data-path', folderPath);
        if (deleteBtn) deleteBtn.setAttribute('data-path', folderPath);
        
        foldersContainer.appendChild(folderCard);
    }
    function renderVideoCard(video) {
        if (!videoTemplate || !videosContainer) return;
        
        const videoCard = videoTemplate.content.cloneNode(true);
        const videoNameText = videoCard.querySelector('.video-name-text');
        const videoInfoText = videoCard.querySelector('.video-info');
        const videoDuration = videoCard.querySelector('.video-duration');
        const previewBtn = videoCard.querySelector('.preview-video');
        const previewVideoBtnSmall = videoCard.querySelector('.preview-video-btn');
        const renameBtn = videoCard.querySelector('.rename-video');
        const moveBtn = videoCard.querySelector('.move-video');
        const deleteBtn = videoCard.querySelector('.delete-video');
        
        if (videoNameText) videoNameText.textContent = video.name;
        if (videoInfoText) videoInfoText.textContent = `Размер: ${formatFileSize(video.size || 0)} • ${video.created || 'Н/Д'}`;
        if (videoDuration) videoDuration.textContent = video.duration || '00:00';
        
        const videoPath = currentPath ? `${currentPath}/${video.name}` : video.name;

        const dbName = $('.container').data('database-name');

        const videoUrl = `/static/video/${dbName}/${videoPath}`;
        if (previewBtn) {
            previewBtn.setAttribute('data-path', videoPath);
            previewBtn.setAttribute('data-url', videoUrl);
        }
        if (previewVideoBtnSmall) {
            previewVideoBtnSmall.setAttribute('data-path', videoPath);
            previewVideoBtnSmall.setAttribute('data-url', videoUrl);
        }
        if (renameBtn) renameBtn.setAttribute('data-path', videoPath);
        if (moveBtn) moveBtn.setAttribute('data-path', videoPath);
        if (deleteBtn) deleteBtn.setAttribute('data-path', videoPath);
        
        videosContainer.appendChild(videoCard);
    }
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Байт';
        const k = 1024;
        const sizes = ['Байт', 'КБ', 'МБ', 'ГБ', 'ТБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    function updateFoldersList() {
        const csrfToken = $('meta[name=csrf-token]').attr('content');

        $.ajax({
            url: '/secondary_admin/get_folders_list',
            method: 'GET',
            beforeSend: function(xhr) {
                if (csrfToken) {
                    xhr.setRequestHeader('X-CSRFToken', csrfToken);
                }
            },
            success: function(response) {
                if (response.status === 'success') {
                    const targetFolderSelect = document.getElementById('targetFolder');
                    if (targetFolderSelect) {
                        targetFolderSelect.innerHTML = '';
                        
                        response.folders.forEach(folder => {
                            const option = document.createElement('option');
                            option.value = folder;
                            option.textContent = folder || '/';
                            targetFolderSelect.appendChild(option);
                        });
                    }
                }
            },
            error: function(xhr) {
            }
        });
    }
    function showRenameModal(type, path, currentName) {
        const modal = $('#renameModal');
        const renameItemType = document.getElementById('renameItemType');
        const renameItemPath = document.getElementById('renameItemPath');
        const newNameInput = document.getElementById('newName');
        
        if (renameItemType) renameItemType.value = type;
        if (renameItemPath) renameItemPath.value = path;
        if (newNameInput) newNameInput.value = currentName;
        
        modal.modal('show');
    }
    function showMoveModal(type, path) {
        const modal = $('#moveModal');
        const moveItemType = document.getElementById('moveItemType');
        const moveItemPath = document.getElementById('moveItemPath');
        
        if (moveItemType) moveItemType.value = type;
        if (moveItemPath) moveItemPath.value = path;
        
        updateFoldersList();
        modal.modal('show');
    }
    function showVideoPreview(path) {
        const modal = $('#previewVideoModal');
        const videoPlayer = document.getElementById('previewVideoPlayer');
        const dbName = $('.container').data('database-name');

        if (!dbName) {
            showVideoNotification('Критическая ошибка: не удалось определить путь к видео.', 'danger');
            return;
        }
        const videoUrl = `/static/video/${dbName}/${path}`;
        
        if (videoPlayer) {
            videoPlayer.src = videoUrl;
            videoPlayer.load();
        }
        
        modal.modal('show');
        modal.on('hidden.bs.modal', function() {
            if (videoPlayer) {
                videoPlayer.pause();
                videoPlayer.src = '';
            }
        });
    }
    function showDeleteConfirmation(type, path, name) {
        const modal = $('#confirmDeleteModal');
        const confirmText = document.getElementById('confirmDeleteText');
        const deleteItemType = document.getElementById('deleteItemType');
        const deleteItemPath = document.getElementById('deleteItemPath');
        
        const typeText = type === 'folder' ? 'папку' : 'видеофайл';
        
        if (confirmText) confirmText.textContent = `Вы уверены, что хотите удалить ${typeText} "${name}"?`;
        if (deleteItemType) deleteItemType.value = type;
        if (deleteItemPath) deleteItemPath.value = path;
        
        modal.modal('show');
    }
    $(document).ready(function() {
        $('#createFolderBtn').off('click').on('click', function() {
            $('#createFolderModal').modal('show');
        });
        $('#uploadVideoBtn').off('click').on('click', function() {
            $('#uploadVideoModal').modal('show');
        });
        const csrfToken = $('meta[name=csrf-token]').attr('content');
        $('#createFolderForm').off('submit').on('submit', function(e) {
            e.preventDefault();
            
            const folderName = $('#folderName').val();
            if (!folderName) {
                showVideoNotification('Введите название папки', 'warning');
                return;
            }
            
            $.ajax({
                url: '/secondary_admin/create_folder',
                method: 'POST',
                data: {
                    path: currentPath,
                    name: folderName
                },
                beforeSend: function(xhr) {
                    if (csrfToken) {
                        xhr.setRequestHeader('X-CSRFToken', csrfToken);
                    }
                },
                success: function(response) {
                    if (response.status === 'success') {
                        $('#createFolderModal').modal('hide');
                        $('#folderName').val('');
                        showVideoNotification('Папка успешно создана', 'success');
                        loadDirectoryContents(currentPath);
                    } else {
                        showVideoNotification('Ошибка при создании папки: ' + response.message, 'danger');
                    }
                },
                error: function(xhr) {
                    showVideoNotification('Ошибка при создании папки', 'danger');
                }
            });
        });
        $('#uploadVideoModal').on('show.bs.modal', function () {
            $('#uploadVideoForm')[0].reset();
            $('.custom-file-label').text('Выберите файлы...');
            $('#uploadProgressContainer').hide();
            $('#upload-progress-list').html('');
            $('#uploadSubmitBtn').prop('disabled', false).html('<i class="fas fa-upload mr-1"></i> Загрузить');
            $('#uploadCancelBtn').prop('disabled', false).text('Отмена');
            $('#uploadCancelBtn').off('click').on('click', function() {
                $('#uploadVideoModal').modal('hide');
            });
        });
        $('#uploadVideoForm').off('submit').on('submit', function(e) {
            e.preventDefault();
            
            const files = document.getElementById('videoFile').files;
            if (files.length === 0) {
                showVideoNotification('Выберите файлы для загрузки', 'warning');
                return;
            }

            const uploadProgressContainer = $('#uploadProgressContainer');
            const progressList = $('#upload-progress-list');
            const submitBtn = $('#uploadSubmitBtn');
            const cancelBtn = $('#uploadCancelBtn');
            submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-2"></i> Загрузка...');
            cancelBtn.prop('disabled', true);
            progressList.html('');
            uploadProgressContainer.show();
            
            let uploadedCount = 0;
            let errorCount = 0;
            const totalFiles = files.length;
            const csrfToken = $('meta[name=csrf-token]').attr('content');
            const uploadPromises = Array.from(files).map((file, index) => {
                return new Promise((resolve, reject) => {
                    const fileId = `file-progress-${index}`;
                    const progressItem = $(`
                        <div class="mb-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-truncate" style="max-width: 70%;">${file.name}</small>
                                <small id="${fileId}-status" class="text-muted">Ожидание...</small>
                            </div>
                            <div class="progress" style="height: 10px;">
                                <div id="${fileId}-bar" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                        </div>
                    `);
                    progressList.append(progressItem);

                    const formData = new FormData();
                    formData.append('path', currentPath);
                    formData.append('video', file);

                    $.ajax({
                        url: '/secondary_admin/upload_video',
                        method: 'POST',
                        data: formData,
                        processData: false,
                        contentType: false,
                        beforeSend: function(xhr) {
                            if (csrfToken) {
                                xhr.setRequestHeader('X-CSRFToken', csrfToken);
                            }
                            $(`#${fileId}-status`).text('Загрузка...').removeClass('text-muted');
                        },
                        xhr: function() {
                            const xhr = new window.XMLHttpRequest();
                            xhr.upload.addEventListener('progress', function(e) {
                                if (e.lengthComputable) {
                                    const percentComplete = (e.loaded / e.total) * 100;
                                    $(`#${fileId}-bar`).css('width', percentComplete + '%');
                                }
                            }, false);
                            return xhr;
                        },
                        success: function(response) {
                            if (response.status === 'success') {
                                uploadedCount++;
                                $(`#${fileId}-bar`).addClass('bg-success');
                                $(`#${fileId}-status`).html('<i class="fas fa-check-circle text-success"></i> Готово');
                                resolve(response);
                            } else {
                                errorCount++;
                                $(`#${fileId}-bar`).addClass('bg-danger');
                                $(`#${fileId}-status`).html(`<i class="fas fa-times-circle text-danger"></i> Ошибка`);
                                reject(response);
                            }
                        },
                        error: function(xhr) {
                            errorCount++;
                            $(`#${fileId}-bar`).addClass('bg-danger');
                            $(`#${fileId}-status`).html(`<i class="fas fa-times-circle text-danger"></i> Ошибка`);
                            reject(xhr);
                        }
                    });
                });
            });
            Promise.allSettled(uploadPromises).then(() => {
                let message = `Загрузка завершена. Успешно: ${uploadedCount} из ${totalFiles}.`;
                let type = 'success';

                if (errorCount > 0) {
                    message = `Загрузка завершена. Успешно: ${uploadedCount}, с ошибками: ${errorCount}.`;
                    type = uploadedCount > 0 ? 'warning' : 'danger';
                }

                showVideoNotification(message, type);
                if (uploadedCount > 0) {
                    loadDirectoryContents(currentPath);
                }
                submitBtn.prop('disabled', false).html('<i class="fas fa-upload mr-1"></i> Загрузить еще');
                cancelBtn.prop('disabled', false).text('Закрыть');
                cancelBtn.off('click').on('click', function() {
                    $('#uploadVideoModal').modal('hide');
                });
            });
        });
        $('#renameForm').off('submit').on('submit', function(e) {
            e.preventDefault();
            
            const type = $('#renameItemType').val();
            const path = $('#renameItemPath').val();
            const newName = $('#newName').val();
            
            if (!newName) {
                showVideoNotification('Введите новое имя', 'warning');
                return;
            }
            
            $.ajax({
                url: '/secondary_admin/rename_item',
                method: 'POST',
                data: {
                    type: type,
                    path: path,
                    new_name: newName
                },
                beforeSend: function(xhr) {
                    if (csrfToken) {
                        xhr.setRequestHeader('X-CSRFToken', csrfToken);
                    }
                },
                success: function(response) {
                    if (response.status === 'success') {
                        $('#renameModal').modal('hide');
                        showVideoNotification('Переименование выполнено успешно', 'success');
                        loadDirectoryContents(currentPath);
                    } else {
                        showVideoNotification('Ошибка при переименовании: ' + response.message, 'danger');
                    }
                },
                error: function(xhr) {
                    showVideoNotification('Ошибка при переименовании', 'danger');
                }
            });
        });
        $('#moveForm').off('submit').on('submit', function(e) {
            e.preventDefault();
            
            const type = $('#moveItemType').val();
            const path = $('#moveItemPath').val();
            const targetFolder = $('#targetFolder').val();
            
            $.ajax({
                url: '/secondary_admin/move_item',
                method: 'POST',
                data: {
                    type: type,
                    path: path,
                    target_folder: targetFolder
                },
                beforeSend: function(xhr) {
                    if (csrfToken) {
                        xhr.setRequestHeader('X-CSRFToken', csrfToken);
                    }
                },
                success: function(response) {
                    if (response.status === 'success') {
                        $('#moveModal').modal('hide');
                        showVideoNotification('Перемещение выполнено успешно', 'success');
                        loadDirectoryContents(currentPath);
                    } else {
                        showVideoNotification('Ошибка при перемещении: ' + response.message, 'danger');
                    }
                },
                error: function(xhr) {
                    showVideoNotification('Ошибка при перемещении', 'danger');
                }
            });
        });
        $('#confirmDeleteBtn').off('click').on('click', function() {
            const type = $('#deleteItemType').val();
            const path = $('#deleteItemPath').val();
            
            $.ajax({
                url: '/secondary_admin/delete_item',
                method: 'POST',
                data: {
                    type: type,
                    path: path
                },
                beforeSend: function(xhr) {
                    if (csrfToken) {
                        xhr.setRequestHeader('X-CSRFToken', csrfToken);
                    }
                },
                success: function(response) {
                    if (response.status === 'success') {
                        $('#confirmDeleteModal').modal('hide');
                        showVideoNotification('Удаление выполнено успешно', 'success');
                        loadDirectoryContents(currentPath);
                    } else {
                        showVideoNotification('Ошибка при удалении: ' + response.message, 'danger');
                    }
                },
                error: function(xhr) {
                    showVideoNotification('Ошибка при удалении', 'danger');
                }
            });
        });
        
        $('#videoFile').off('change').on('change', function() {
            const files = $(this)[0].files;
            if (files.length > 1) {
                $(this).next('.custom-file-label').text(`Выбрано файлов: ${files.length}`);
            } else if (files.length === 1) {
                const fileName = files[0].name;
                $(this).next('.custom-file-label').text(fileName);
            } else {
                $(this).next('.custom-file-label').text('Выберите файлы...');
            }
        });
        $('#videoSearchInput').off('keyup').on('keyup', function() {
            const searchValue = $(this).val().toLowerCase();
            $('.folder-card').each(function() {
                const folderName = $(this).find('.folder-name-text').text().toLowerCase();
                $(this).toggle(folderName.indexOf(searchValue) > -1);
            });
            $('.video-card').each(function() {
                const videoName = $(this).find('.video-name-text').text().toLowerCase();
                $(this).toggle(videoName.indexOf(searchValue) > -1);
            });
            const visibleFolders = $('.folder-card:visible').length;
            if (visibleFolders === 0) {
                $('#no-folders-message').show();
            } else {
                $('#no-folders-message').hide();
            }
            const visibleVideos = $('.video-card:visible').length;
            if (visibleVideos === 0) {
                $('#no-videos-message').show();
            } else {
                $('#no-videos-message').hide();
            }
        });

        $(document).off('click', '.rename-folder').on('click', '.rename-folder', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const path = String($(this).data('path') || '');
            if (!path) {
                showVideoNotification('Некорректный путь', 'danger');
                return;
            }
            const name = path.split('/').pop();
            showRenameModal('folder', path, name);
        });

        $(document).off('click', '.rename-video').on('click', '.rename-video', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const path = String($(this).data('path') || '');
            if (!path) {
                showVideoNotification('Некорректный путь', 'danger');
                return;
            }
            const name = path.split('/').pop();
            showRenameModal('video', path, name);
        });

        $(document).off('click', '.move-folder').on('click', '.move-folder', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const path = String($(this).data('path') || '');
            if (!path) {
                showVideoNotification('Некорректный путь', 'danger');
                return;
            }
            showMoveModal('folder', path);
        });

        $(document).off('click', '.move-video').on('click', '.move-video', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const path = String($(this).data('path') || '');
            if (!path) {
                showVideoNotification('Некорректный путь', 'danger');
                return;
            }
            showMoveModal('video', path);
        });

        $(document).off('click', '.delete-folder').on('click', '.delete-folder', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const path = String($(this).data('path') || '');
            if (!path) {
                showVideoNotification('Некорректный путь', 'danger');
                return;
            }
            const name = path.split('/').pop();
            showDeleteConfirmation('folder', path, name);
        });

        $(document).off('click', '.delete-video').on('click', '.delete-video', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const path = String($(this).data('path') || '');
            if (!path) {
                showVideoNotification('Некорректный путь', 'danger');
                return;
            }
            const name = path.split('/').pop();
            showDeleteConfirmation('video', path, name);
        });

        $(document).off('click', '.preview-video, .preview-video-btn').on('click', '.preview-video, .preview-video-btn', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const videoPath = String($(this).data('path') || '');
            if (!videoPath) {
                showVideoNotification('Некорректный путь', 'danger');
                return;
            }
            showVideoPreview(videoPath);
        });

        $(document).off('click', '.folder-link').on('click', '.folder-link', function(e) {
            e.preventDefault();
            const path = String($(this).data('path') || '');
            loadDirectoryContents(path);
        });

        $(document).off('click', '.open-folder').on('click', '.open-folder', function(e) {
            e.preventDefault();
            const folderPath = String($(this).data('path') || '');
            loadDirectoryContents(folderPath);
        });
        $(document).off('click', '.video-item .dropdown-toggle, .folder-item .dropdown-toggle').on('click', '.video-item .dropdown-toggle, .folder-item .dropdown-toggle', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $('.video-item .dropdown-menu, .folder-item .dropdown-menu').removeClass('show');
            $(this).siblings('.dropdown-menu').addClass('show');
        });
        $(document).off('click.video-dropdown').on('click.video-dropdown', function(e) {
            if (!$(e.target).closest('.video-item .dropdown, .folder-item .dropdown').length) {
                $('.video-item .dropdown-menu, .folder-item .dropdown-menu').removeClass('show');
            }
        });

        $(document).off('click', '.video-item .dropdown-menu, .folder-item .dropdown-menu').on('click', '.video-item .dropdown-menu, .folder-item .dropdown-menu', function(e) {
            e.stopPropagation();
        });

        $(document).off('click', '.video-item .dropdown-item, .folder-item .dropdown-item').on('click', '.video-item .dropdown-item, .folder-item .dropdown-item', function() {
            $(this).closest('.dropdown-menu').removeClass('show');
        });
        $('#videos-tab').off('shown.bs.tab').on('shown.bs.tab', function(e) {
            try {
                loadDiskSpaceInfo();
                
                const savedPath = localStorage.getItem('videoCurrentPath') || '';
                loadDirectoryContents(savedPath);
            } catch (e) {
                loadDirectoryContents('');
            }
        });
        if ($('#videos-tab').hasClass('active')) {
            setTimeout(function() {
                loadDiskSpaceInfo();
                
                try {
                    const savedPath = localStorage.getItem('videoCurrentPath') || '';
                    loadDirectoryContents(savedPath);
                } catch (e) {
                    loadDirectoryContents('');
                }
            }, 200);
        }
    });
    const styleElement = document.createElement('style');
    styleElement.textContent = `

/* Замени CSS стили для dropdown в admin_video.js на эти исправленные: */

        .dropdown-menu {
            display: none;
            position: absolute;
            transform: translate3d(0px, 38px, 0px);
            top: 0;
            left: 0;
            will-change: transform;
            background-color: #243343;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 0.25rem;
            padding: 0.5rem 0;
            margin: 0.125rem 0 0;
            min-width: 10rem;
            z-index: 9999; /* Увеличен z-index */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); /* Добавлена тень */
        }

        .dropdown-menu.show {
            display: block;
        }

        /* Автоматическое позиционирование dropdown справа, если он выходит за край */
        .dropdown.dropright .dropdown-menu {
            top: 0;
            right: 100%;
            left: auto;
            margin-top: 0;
            margin-left: 0;
            margin-right: 0.125rem;
        }

        /* Позиционирование dropdown вверх, если он выходит за нижний край */
        .dropdown.dropup .dropdown-menu {
            top: auto;
            bottom: 100%;
            margin-top: 0;
            margin-bottom: 0.125rem;
        }

        .dropdown-item {
            display: block;
            width: 100%;
            padding: 0.25rem 1.5rem;
            clear: both;
            font-weight: 400;
            color: #ecf0f1;
            text-align: inherit;
            white-space: nowrap;
            background-color: transparent;
            border: 0;
            transition: all 0.2s ease;
            cursor: pointer;
        }

        .dropdown-item:hover, .dropdown-item:focus {
            color: #ffffff;
            text-decoration: none;
            background-color: rgba(26, 188, 156, 0.3);
        }

        .dropdown-item.active, .dropdown-item:active {
            color: #fff;
            text-decoration: none;
            background-color: #1abc9c;
        }

        .dropdown-divider {
            height: 0;
            margin: 0.5rem 0;
            overflow: hidden;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .dropdown-item.text-danger:hover, .dropdown-item.text-danger:focus {
            color: #ffffff !important;
            background-color: rgba(231, 76, 60, 0.3);
        }

        /* Стили для dropdown контейнера */
        .dropdown {
            position: relative;
            z-index: 1000; /* Базовый z-index для dropdown контейнера */
        }

        /* Стили для карточек */
        .folder-card, .video-card {
            margin-bottom: 1rem;
            position: relative; /* Важно для корректного позиционирования dropdown */
        }

        .folder-item, .video-item {
            background-color: #243343;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 0.5rem;
            transition: all 0.3s ease;
            overflow: visible; /* Позволяет dropdown выходить за границы карточки */
            position: relative;
        }

        .folder-item:hover, .video-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            border-color: rgba(26, 188, 156, 0.3);
            z-index: 1001; /* Поднимаем карточку при hover */
        }

        /* Когда dropdown открыт, поднимаем z-index карточки */
        .folder-item:has(.dropdown-menu.show), 
        .video-item:has(.dropdown-menu.show),
        .folder-card:has(.dropdown-menu.show),
        .video-card:has(.dropdown-menu.show) {
            z-index: 10000;
        }

        /* Для браузеров, не поддерживающих :has() */
        .folder-item.dropdown-open, 
        .video-item.dropdown-open,
        .folder-card.dropdown-open,
        .video-card.dropdown-open {
            z-index: 10000;
        }

        .video-thumbnail {
            background: linear-gradient(135deg, #1a2530 0%, #243343 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0.5rem 0.5rem 0 0;
        }

        .play-icon {
            opacity: 0.7;
            transition: opacity 0.3s ease;
        }

        .video-item:hover .play-icon {
            opacity: 1;
        }

        .folder-icon {
            color: #f39c12;
            font-size: 2rem;
        }

        /* Фиксация контейнеров для правильного overflow */
        #folders-container, #videos-container {
            overflow: visible;
        }

        .row {
            overflow: visible;
        }

        /* Стили для dropdown toggle кнопки */
        .dropdown-toggle {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ecf0f1;
            transition: all 0.2s ease;
        }

        .dropdown-toggle:hover {
            background: rgba(26, 188, 156, 0.2);
            border-color: rgba(26, 188, 156, 0.3);
            color: #ffffff;
        }

        .dropdown-toggle:focus {
            box-shadow: 0 0 0 0.2rem rgba(26, 188, 156, 0.25);
        }    `;
    document.head.appendChild(styleElement);
}
$(document).ready(function() {
    initAdminVideo();
    $(document).on('click', '#refreshDiskSpaceBtn', function() {
        loadDiskSpaceInfo();
    });
    if ($('#videos-tab').hasClass('active')) {
        setTimeout(function() {
            loadDiskSpaceInfo();
        }, 300);
    }
    $('#videos-tab').on('shown.bs.tab', function(e) {
        loadDiskSpaceInfo();
    });
});