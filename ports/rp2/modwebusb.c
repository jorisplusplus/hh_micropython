
#include "py/objstr.h"
#include "py/runtime.h"

#ifndef NO_QSTR
#include "tusb.h"
#include "tusb_config.h"
#endif


static mp_obj_t webusb_mode(){
    return mp_obj_new_int(usb_mode);
}
static MP_DEFINE_CONST_FUN_OBJ_0(webusb_mode_obj, webusb_mode);

static mp_obj_t webusb_setmode(mp_obj_t data){
    usb_mode = mp_obj_get_int(data);
    return mp_obj_new_int(usb_mode);
}
static MP_DEFINE_CONST_FUN_OBJ_1(webusb_setmode_obj, webusb_setmode);

static mp_obj_t webusb_send(mp_obj_t data) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data, &bufinfo, MP_BUFFER_READ);

	uint32_t written = tud_vendor_n_write(1, bufinfo.buf, bufinfo.len);

	return mp_obj_new_int(written);
}
static MP_DEFINE_CONST_FUN_OBJ_1(webusb_send_obj, webusb_send);

static mp_obj_t webusb_secretsend(mp_obj_t data) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data, &bufinfo, MP_BUFFER_READ);

	uint32_t written = tud_vendor_n_write(2, bufinfo.buf, bufinfo.len);

	return mp_obj_new_int(written);
}
static MP_DEFINE_CONST_FUN_OBJ_1(webusb_secretsend_obj, webusb_secretsend);

static mp_obj_t webusb_available() {
    return mp_obj_new_int(tud_vendor_n_available(1));
}
static MP_DEFINE_CONST_FUN_OBJ_0(webusb_available_obj, webusb_available);

static mp_obj_t webusb_secretavailable() {
    return mp_obj_new_int(tud_vendor_n_available(2));
}
static MP_DEFINE_CONST_FUN_OBJ_0(webusb_secretavailable_obj, webusb_secretavailable);

static mp_obj_t webusb_write_available() {
    return mp_obj_new_int(tud_vendor_n_write_available(1));
}
static MP_DEFINE_CONST_FUN_OBJ_0(webusb_write_available_obj, webusb_write_available);

static mp_obj_t webusb_secretwrite_available() {
    return mp_obj_new_int(tud_vendor_n_write_available(2));
}
static MP_DEFINE_CONST_FUN_OBJ_0(webusb_secretwrite_available_obj, webusb_secretwrite_available);

static mp_obj_t webusb_read(mp_obj_t data) {
    if (tud_vendor_n_available(1) == 0) {
        return mp_obj_new_int(0);
    }

    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data, &bufinfo, MP_BUFFER_WRITE);

    uint32_t read = tud_vendor_n_read(1, bufinfo.buf, bufinfo.len);
    
    return mp_obj_new_int(read);
}
static MP_DEFINE_CONST_FUN_OBJ_1(webusb_read_obj, webusb_read);

static mp_obj_t webusb_secretread(mp_obj_t data) {
    if (tud_vendor_n_available(1) == 0) {
        return mp_obj_new_int(0);
    }

    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data, &bufinfo, MP_BUFFER_WRITE);

    uint32_t read = tud_vendor_n_read(2, bufinfo.buf, bufinfo.len);
    
    return mp_obj_new_int(read);
}
static MP_DEFINE_CONST_FUN_OBJ_1(webusb_secretread_obj, webusb_secretread);

static const mp_rom_map_elem_t webusb_module_globals_table[] = {
    {MP_OBJ_NEW_QSTR(MP_QSTR_setmode), (mp_obj_t)&webusb_setmode_obj},
    {MP_OBJ_NEW_QSTR(MP_QSTR_mode), (mp_obj_t)&webusb_mode_obj},
	{MP_OBJ_NEW_QSTR(MP_QSTR_read), (mp_obj_t)&webusb_read_obj},
    {MP_OBJ_NEW_QSTR(MP_QSTR_available), (mp_obj_t)&webusb_available_obj},
    {MP_OBJ_NEW_QSTR(MP_QSTR_write_available), (mp_obj_t)&webusb_write_available_obj},
	{MP_OBJ_NEW_QSTR(MP_QSTR_send), (mp_obj_t)&webusb_send_obj},
    {MP_OBJ_NEW_QSTR(MP_QSTR_secretread), (mp_obj_t)&webusb_secretread_obj},
    {MP_OBJ_NEW_QSTR(MP_QSTR_secretavailable), (mp_obj_t)&webusb_secretavailable_obj},
    {MP_OBJ_NEW_QSTR(MP_QSTR_secretwrite_available), (mp_obj_t)&webusb_secretwrite_available_obj},
	{MP_OBJ_NEW_QSTR(MP_QSTR_secretsend), (mp_obj_t)&webusb_secretsend_obj},
};

static MP_DEFINE_CONST_DICT(webusb_module_globals, webusb_module_globals_table);

const mp_obj_module_t mp_webusb_module = {
	.base = {&mp_type_module},
	.globals = (mp_obj_dict_t *)&webusb_module_globals,
};