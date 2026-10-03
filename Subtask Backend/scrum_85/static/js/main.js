/**
 * JAVASCRIPT TƯƠNG TÁC GIAO DIỆN - SCRUM-85
 * Quản lý mở/đóng Modal, hỗ trợ khai báo nhóm con, chỉnh sửa nhóm và khu vực địa lý
 */

// Hàm mở Modal theo ID
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

// Hàm đóng Modal theo ID
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Đóng modal khi bấm phím Escape
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        const activeModals = document.querySelectorAll('.modal-overlay.active');
        activeModals.forEach(m => {
            m.classList.remove('active');
        });
        document.body.style.overflow = '';
    }
});

// Đóng modal khi click ra ngoài vùng backdrop
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// ==============================================================================
// 1. MODAL QUẢN LÝ NHÓM KINH DOANH
// ==============================================================================

function openCreateTeamModal() {
    const parentSelect = document.getElementById('create_parent_id');
    if (parentSelect) {
        parentSelect.value = '';
    }
    openModal('createTeamModal');
}

function openCreateSubteamModal(parentId, parentName, regionId) {
    openModal('createTeamModal');
    const parentSelect = document.getElementById('create_parent_id');
    if (parentSelect) {
        parentSelect.value = parentId;
    }
    const regionSelect = document.getElementById('create_region_id');
    if (regionSelect && regionId) {
        regionSelect.value = regionId;
    }
}

function openEditTeamModal(teamId, name, parentId, leaderId, regionId, description) {
    const form = document.getElementById('editTeamForm');
    if (form) {
        form.action = `/team/update/${teamId}`;
    }
    
    document.getElementById('edit_team_id_display').value = teamId;
    document.getElementById('edit_name').value = name;
    
    const parentSelect = document.getElementById('edit_parent_id');
    if (parentSelect) {
        parentSelect.value = parentId || '';
        // Disable chính nó trong dropdown để tránh chọn chính mình làm cha
        Array.from(parentSelect.options).forEach(opt => {
            if (opt.value === teamId) {
                opt.disabled = true;
                opt.text = `${opt.text} (Không thể chọn chính mình)`;
            } else {
                opt.disabled = false;
            }
        });
    }

    const leaderSelect = document.getElementById('edit_leader_id');
    if (leaderSelect) {
        leaderSelect.value = leaderId;
    }

    const regionSelect = document.getElementById('edit_region_id');
    if (regionSelect) {
        regionSelect.value = regionId;
    }

    const descField = document.getElementById('edit_description');
    if (descField) {
        descField.value = description || '';
    }

    openModal('editTeamModal');
}

// ==============================================================================
// 2. MODAL ĐIỀU CHUYỂN NHÂN SỰ (TIÊU CHÍ 2)
// ==============================================================================

function openTransferModal() {
    openModal('transferModal');
}

function openAddEmployeeModal() {
    openModal('addEmployeeModal');
}

function openTransferForEmp(empId, empName, currentTeamId, currentTeamName) {
    openModal('transferModal');
    const empSelect = document.getElementById('transfer_emp_id');
    if (empSelect) {
        empSelect.value = empId;
        onSelectTransferEmp(empSelect);
    }
}

function onSelectTransferEmp(selectElem) {
    const selectedOption = selectElem.options[selectElem.selectedIndex];
    const noticeBox = document.getElementById('transferNoticeBox');
    const oldTeamSpan = document.getElementById('noticeOldTeamName');
    const newTeamSelect = document.getElementById('transfer_new_team_id');

    if (selectedOption && selectedOption.value) {
        const teamName = selectedOption.getAttribute('data-current-team');
        const teamId = selectedOption.getAttribute('data-team-id');

        if (noticeBox && oldTeamSpan) {
            oldTeamSpan.textContent = teamName || 'Chưa gán';
            noticeBox.style.display = 'block';
        }

        // Tự động bỏ chọn nhóm hiện tại khỏi nhóm đích
        if (newTeamSelect) {
            Array.from(newTeamSelect.options).forEach(opt => {
                if (opt.value === teamId) {
                    opt.disabled = true;
                } else {
                    opt.disabled = false;
                }
            });
        }
    } else {
        if (noticeBox) noticeBox.style.display = 'none';
    }
}

// ==============================================================================
// 3. MODAL QUẢN LÝ KHU VỰC ĐỊA LÝ (TIÊU CHÍ 4)
// ==============================================================================

function openCreateRegionModal() {
    openModal('createRegionModal');
}

function openEditRegionModal(regId, name, code, provinces, description, badgeColor) {
    const form = document.getElementById('editRegionForm');
    if (form) {
        form.action = `/region/update/${regId}`;
    }

    document.getElementById('edit_reg_id_display').value = regId;
    document.getElementById('edit_reg_name').value = name;
    document.getElementById('edit_reg_code').value = code || '';
    document.getElementById('edit_reg_provinces').value = provinces || '';
    document.getElementById('edit_reg_description').value = description || '';
    
    const colorInput = document.getElementById('edit_reg_badge_color');
    if (colorInput && badgeColor) {
        colorInput.value = badgeColor;
    }

    openModal('editRegionModal');
}
