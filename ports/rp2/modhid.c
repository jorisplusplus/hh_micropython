
#include "py/objstr.h"
#include "py/runtime.h"

#ifndef NO_QSTR
#include "tusb.h"
#include "tusb_config.h"
#endif

static mp_obj_t hid_keyboard(mp_obj_t modifiers, mp_obj_t data) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data, &bufinfo, MP_BUFFER_READ);

    tud_hid_keyboard_report(REPORT_ID_KEYBOARD, mp_obj_get_int(modifiers), bufinfo.buf);

	return mp_obj_new_int(0);
}
static MP_DEFINE_CONST_FUN_OBJ_2(hid_keyboard_obj, hid_keyboard);

static mp_obj_t hid_mouse(size_t n_args, const mp_obj_t *args) {
    if (n_args != 5) {
        mp_raise_TypeError(MP_ERROR_TEXT("Needs args button, x, y, horizontal, vertical"));
    }
    tud_hid_mouse_report(REPORT_ID_MOUSE, mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), mp_obj_get_int(args[2]), mp_obj_get_int(args[3]), mp_obj_get_int(args[4]));

	return mp_obj_new_int(0);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(hid_mouse_obj, 5, 5, hid_mouse);

static const mp_rom_map_elem_t hid_module_globals_table[] = {
	{MP_OBJ_NEW_QSTR(MP_QSTR_keyboard), (mp_obj_t)&hid_keyboard_obj},
    {MP_OBJ_NEW_QSTR(MP_QSTR_mouse), (mp_obj_t)&hid_mouse_obj}
};

static MP_DEFINE_CONST_DICT(hid_module_globals, hid_module_globals_table);

const mp_obj_module_t mp_hid_module = {
	.base = {&mp_type_module},
	.globals = (mp_obj_dict_t *)&hid_module_globals,
};