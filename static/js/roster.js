// Roster Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Color picker synchronization
    const colorInputs = document.querySelectorAll('input[type="color"]');
    const colorTextInputs = document.querySelectorAll('input[type="text"][pattern*="[0-9A-Fa-f]{6}"]');
    
    colorInputs.forEach((input, index) => {
        const textInput = colorTextInputs[index];
        if (textInput) {
            input.addEventListener('input', () => {
                textInput.value = input.value;
            });
            
            textInput.addEventListener('input', () => {
                if (textInput.value.match(/^#[0-9A-Fa-f]{6}$/)) {
                    input.value = textInput.value;
                }
            });
        }
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Date validation for override form
    const startDate = document.getElementById('override_start_date');
    const endDate = document.getElementById('override_end_date');
    
    if (startDate && endDate) {
        startDate.addEventListener('change', () => {
            endDate.min = startDate.value;
            if (endDate.value && endDate.value < startDate.value) {
                endDate.value = startDate.value;
            }
        });
        
        endDate.addEventListener('change', () => {
            if (startDate.value && endDate.value < startDate.value) {
                endDate.value = startDate.value;
            }
        });
    }

    // Auto-dismiss alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Enhanced table interactions
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function(e) {
            if (!e.target.closest('button') && !e.target.closest('a') && !e.target.closest('input')) {
                this.classList.toggle('table-active');
            }
        });
    });

    // Initialize rotation toggles
    initializeRotationToggles();
    
    // Initialize drag and drop
    initializeDragAndDrop();
    
    // Initialize save button state
    initializeSaveButton();
});

// Rotation toggle functionality
function initializeRotationToggles() {
    const rotationToggles = document.querySelectorAll('.rotation-toggle');
    
    rotationToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const memberName = this.getAttribute('data-member');
            const isChecked = this.checked;
            
            // Send AJAX request to toggle rotation
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            fetch('/standby/roster/toggle_rotation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: `name=${encodeURIComponent(memberName)}&add_to_rotation=${isChecked}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (isChecked) {
                        addToRotation(memberName);
                    } else {
                        removeFromRotation(memberName);
                    }
                    showToast('Success', data.message, 'success');
                } else {
                    // Revert the toggle if the request failed
                    this.checked = !isChecked;
                    showToast('Error', data.message, 'error');
                }
            })
            .catch(error => {
                // Revert the toggle if the request failed
                this.checked = !isChecked;
                showToast('Error', 'Failed to update rotation', 'error');
                console.error('Error:', error);
            });
        });
    });
}

function addToRotation(memberName) {
    const rotationList = document.getElementById('rotationList');
    if (!rotationList) return;
    
    // Create new rotation item
    const rotationItem = document.createElement('div');
    rotationItem.className = 'rotation-item';
    rotationItem.setAttribute('data-person', memberName);
    rotationItem.setAttribute('draggable', 'true');
    
    const maxOrder = rotationList.children.length;
    rotationItem.innerHTML = `
        <div class="drag-handle">
            <i class="bi bi-grip-vertical text-muted"></i>
        </div>
        <div class="rotation-content">
            <span class="rotation-number">${maxOrder + 1}</span>
            <span class="rotation-name">${memberName}</span>
        </div>
        <div class="rotation-actions">
            <button type="button" class="btn btn-sm btn-outline-primary move-btn" 
                    onclick="movePersonByName('${memberName}', 'up')" 
                    ${maxOrder === 0 ? 'disabled' : ''} title="Move up">
                <i class="bi bi-arrow-up"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-primary move-btn" 
                    onclick="movePersonByName('${memberName}', 'down')" 
                    title="Move down">
                <i class="bi bi-arrow-down"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger remove-btn" 
                    onclick="removePerson('${memberName}')" title="Remove from rotation">
                <i class="bi bi-trash"></i>
            </button>
        </div>
        <input type="hidden" name="rotation[]" value="${memberName}">
    `;
    
    rotationList.appendChild(rotationItem);
    updateRotationNumbers();
    
    // Show success toast
    showToast('Success', `${memberName} added to rotation`, 'success');
}

function removeFromRotation(memberName) {
    const rotationItem = document.querySelector(`[data-person="${memberName}"]`);
    if (rotationItem) {
        rotationItem.remove();
        updateRotationNumbers();
        
        // Show success toast
        showToast('Success', `${memberName} removed from rotation`, 'success');
    }
}

// Drag and drop functionality
function initializeDragAndDrop() {
    const rotationList = document.getElementById('rotationList');
    if (!rotationList) return;
    
    let draggedItem = null;
    
    rotationList.addEventListener('dragstart', function(e) {
        draggedItem = e.target;
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', e.target.outerHTML);
    });
    
    rotationList.addEventListener('dragend', function(e) {
        e.target.classList.remove('dragging');
        draggedItem = null;
    });
    
    rotationList.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const targetItem = e.target.closest('.rotation-item');
        if (targetItem && targetItem !== draggedItem) {
            const rect = targetItem.getBoundingClientRect();
            const midpoint = rect.top + rect.height / 2;
            
            if (e.clientY < midpoint) {
                targetItem.classList.add('drag-over');
                targetItem.classList.remove('drag-over-bottom');
            } else {
                targetItem.classList.add('drag-over-bottom');
                targetItem.classList.remove('drag-over');
            }
        }
    });
    
    rotationList.addEventListener('dragleave', function(e) {
        const targetItem = e.target.closest('.rotation-item');
        if (targetItem) {
            targetItem.classList.remove('drag-over', 'drag-over-bottom');
        }
    });
    
    rotationList.addEventListener('drop', function(e) {
        e.preventDefault();
        
        const targetItem = e.target.closest('.rotation-item');
        if (targetItem && draggedItem && targetItem !== draggedItem) {
            const rect = targetItem.getBoundingClientRect();
            const midpoint = rect.top + rect.height / 2;
            
            if (e.clientY < midpoint) {
                rotationList.insertBefore(draggedItem, targetItem);
            } else {
                rotationList.insertBefore(draggedItem, targetItem.nextSibling);
            }
            
            updateRotationNumbers();
            updateSaveButtonState();
            
            // Show success toast
            showToast('Success', 'Rotation order updated. Click "Save Changes" to persist.', 'success');
        }
        
        // Remove drag-over classes
        document.querySelectorAll('.rotation-item').forEach(item => {
            item.classList.remove('drag-over', 'drag-over-bottom');
        });
    });
}

// Save button functionality
function initializeSaveButton() {
    const saveBtn = document.getElementById('saveRotationBtn');
    const rotationForm = document.getElementById('rotationForm');
    
    if (saveBtn && rotationForm) {
        rotationForm.addEventListener('submit', function(e) {
            if (saveBtn.disabled) {
                e.preventDefault();
                return;
            }
            
            // Show loading state
            saveBtn.classList.add('loading');
            saveBtn.disabled = true;
            
            // Validate that there are rotation items
            const rotationItems = document.querySelectorAll('#rotationList .rotation-item');
            if (rotationItems.length === 0) {
                e.preventDefault();
                saveBtn.classList.remove('loading');
                saveBtn.disabled = false;
                showToast('Warning', 'No rotation items to save', 'warning');
                return;
            }
            
            // The form will submit normally, and the page will reload with flash messages
            // The loading state will be cleared on page reload
        });
    }
}

function updateSaveButtonState() {
    const saveBtn = document.getElementById('saveRotationBtn');
    if (saveBtn) {
        // Enable save button when there are changes
        saveBtn.disabled = false;
    }
}

// Toast notification system
function showToast(title, message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast show`;
    toast.id = toastId;
    
    const iconMap = {
        'success': 'bi-check-circle-fill text-success',
        'error': 'bi-exclamation-triangle-fill text-danger',
        'warning': 'bi-exclamation-triangle-fill text-warning',
        'info': 'bi-info-circle-fill text-info'
    };
    
    toast.innerHTML = `
        <div class="toast-header">
            <i class="bi ${iconMap[type] || iconMap.info} me-2"></i>
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove toast after 5 seconds
    setTimeout(() => {
        const toastElement = document.getElementById(toastId);
        if (toastElement) {
            toastElement.remove();
        }
    }, 5000);
}

// Global functions for rotation management
function movePerson(index, direction) {
    const list = document.getElementById('rotationList');
    const items = Array.from(list.querySelectorAll('.rotation-item'));
    if (direction === 'up' && index > 0) {
        list.insertBefore(items[index], items[index - 1]);
    } else if (direction === 'down' && index < items.length - 1) {
        list.insertBefore(items[index + 1], items[index]);
    }
    updateRotationNumbers();
    updateSaveButtonState();
}

// New function to move by person name
function movePersonByName(person, direction) {
    const list = document.getElementById('rotationList');
    const items = Array.from(list.querySelectorAll('.rotation-item'));
    const index = items.findIndex(item => item.getAttribute('data-person') === person);
    if (index !== -1) {
        movePerson(index, direction);
        showToast('Success', `Moved ${person} ${direction}`, 'success');
    }
}

function removePerson(person) {
    if (confirm(`Remove ${person} from rotation?`)) {
        const item = document.querySelector(`[data-person="${person}"]`);
        if (item) {
            item.remove();
            updateRotationNumbers();
            updateSaveButtonState();
            
            // Update the toggle in the member table
            const toggle = document.querySelector(`#rotation_${person.replace(' ', '_')}`);
            if (toggle) {
                toggle.checked = false;
            }
            
            showToast('Success', `${person} removed from rotation`, 'success');
        }
    }
}

function updateRotationNumbers() {
    const items = document.querySelectorAll('#rotationList .rotation-item');
    items.forEach((item, index) => {
        const numberSpan = item.querySelector('.rotation-number');
        if (numberSpan) {
            numberSpan.textContent = index + 1;
        }
        
        // Update move button states
        const upBtn = item.querySelector('[onclick*="up"]');
        const downBtn = item.querySelector('[onclick*="down"]');
        
        if (upBtn) upBtn.disabled = index === 0;
        if (downBtn) downBtn.disabled = index === items.length - 1;
    });
}

function editMember(name, color, active) {
    document.getElementById('edit_name_original').value = name;
    document.getElementById('edit_name').value = name;
    document.getElementById('edit_color').value = color;
    document.getElementById('edit_colorText').value = color;
    document.getElementById('edit_active').checked = active;
    
    const modal = new bootstrap.Modal(document.getElementById('editMemberModal'));
    modal.show();
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case 'n':
                e.preventDefault();
                const addModal = new bootstrap.Modal(document.getElementById('addMemberModal'));
                addModal.show();
                break;
            case 'o':
                e.preventDefault();
                const overrideModal = new bootstrap.Modal(document.getElementById('addOverrideModal'));
                overrideModal.show();
                break;
        }
    }
});

// Global functions for team member management
function removeFromTeam(memberName) {
    if (confirm(`Are you sure you want to remove ${memberName} from the team? This will also remove them from rotation if they are currently in it.`)) {
        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
        
        // Send AJAX request to remove from team
        fetch('/standby/roster/remove_member', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `name=${encodeURIComponent(memberName)}`
        })
        .then(response => {
            if (response.ok) {
                // Reload the page to show updated team
                window.location.reload();
            } else {
                throw new Error('Failed to remove member');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to remove member from team. Please try again.');
        });
    }
}

// Global functions for team member management
function addToRotationFromTable(memberName) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    
    // Send AJAX request to add to rotation
    fetch('/standby/roster/update_rotation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `add=${encodeURIComponent(memberName)}`
    })
    .then(response => {
        if (response.ok) {
            // Reload the page to show updated rotation
            window.location.reload();
        } else {
            throw new Error('Failed to add to rotation');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to add member to rotation. Please try again.');
    });
} 